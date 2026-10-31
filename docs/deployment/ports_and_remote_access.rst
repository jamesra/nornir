Ports and remote access
=======================

.. _deploy-firewall-request:

Firewall request
----------------

Send this table to Pitt IT. "Campus/VPN" means the Pitt campus network and the Pitt VPN
(GlobalProtect); Pitt typically requires the VPN for SSH from off campus (confirm with Pitt IT).

.. list-table::
   :header-rows: 1
   :widths: 12 18 22 48

   * - Host
     - Port
     - Allow from
     - Why
   * - ``web``
     - 22/tcp
     - campus/VPN
     - SSH for deploys (``stack.ps1 -Target web``), key-only
   * - ``web``
     - 80/tcp
     - internet
     - Let's Encrypt HTTP-01 validation and http-to-https redirect. Only needed for
       ``TLS_MODE=letsencrypt``; otherwise campus only or closed.
   * - ``web``
     - 443/tcp
     - internet
     - Every public Viking name (SNI passthrough)
   * - ``compute``
     - 22/tcp
     - campus/VPN
     - SSH for deploys and tunnels
   * - ``compute``
     - 40443/tcp; 40444/tcp; 40445/tcp and up
     - ``web`` only
     - ``viking-segmentation`` with published ports (the compose default), reached by the proxy:
       the default model on 40443, its demo page on 40444 (only when enabled), and one port per
       ``models.json`` row with ``"network": "published"``, numbered from 40445. Not needed for
       servers on macvlan or the backend network (:ref:`deploy-segmentation-network`).
   * - segmentation IP
     - 443/tcp
     - ``web`` only
     - Only when the segmentation server runs on its own MAC and IP (macvlan). A network ACL:
       the host firewall does not see this traffic. If the server reads local tilesets, also
       outbound from that IP to the identity and ``websvc`` hosts.
   * - ``compute``
     - 445/tcp outbound
     - to the NAS
     - CIFS mounts for ``nornir-build``
   * - ``iis``
     - 443/tcp
     - ``web`` only
     - IIS sites behind ``websvc.<domain>``
   * - ``iis``
     - 22/tcp
     - campus/VPN
     - Windows OpenSSH for ``stack.ps1 -Target iis``
   * - SQL Server
     - 1433/tcp
     - ``web`` and ``iis`` only
     - Identity, annotation, and IIS databases

Never open these to the network; reach them through an SSH tunnel:

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Port
     - Service
   * - 1883
     - Mosquitto (dashboard broker; unauthenticated)
   * - 8087
     - Build dashboard
   * - 4024
     - .NET remote debugger (vsdbg)
   * - 5678
     - debugpy
   * - 81
     - Nginx Proxy Manager admin UI (old layout; removed)
   * - 2375 / 2376
     - Docker daemon API
   * - 5985 / 5986
     - WinRM
   * - 3389
     - Remote Desktop (use it over the VPN or an SSH tunnel if at all)

The service ports on ``web`` (Identity 5001/6001/4001, annotation 5010/5011, corrections
41080/41443, the Sam2Trainer annotation gallery 8442) are internal: the proxy reaches them on the
host. They are not part of the firewall request. Viking's per-port table is
:viking:`Viking ports and remote access <ports_and_remote_access.html>`.

Docker and ufw on Linux
-----------------------

Ports published by Docker (``ports:`` in compose, ``-p`` in ``docker run``) are inserted into
iptables ahead of ufw's rules, so **ufw does not filter them**. Two rules follow:

* Internal ports are published on ``127.0.0.1`` only (the dashboard and broker templates do this:
  ``NORNIR_DASHBOARD_BIND_HOST=127.0.0.1``, ``NORNIR_MQTT_BIND_HOST=127.0.0.1``). Do not widen
  them.
* Ports another host must reach are filtered in the ``DOCKER-USER`` chain, which Docker evaluates
  before its own rules and never rewrites.

On ``compute``, allow only ``web`` to reach the published segmentation ports. Replace the
interface name (``ip -br link``) and the address of ``web``, and widen the port range to the
highest ``port`` in ``models.json``::

   EXT_IF=eno1
   WEB_IP=203.0.113.10
   # Inserted in reverse order: the ACCEPT ends up above the DROP.
   sudo iptables -I DOCKER-USER -i "$EXT_IF" -p tcp -m conntrack --ctorigdstport 40443:40449 --ctdir ORIGINAL -j DROP
   sudo iptables -I DOCKER-USER -i "$EXT_IF" -p tcp -s "$WEB_IP" -m conntrack --ctorigdstport 40443:40449 --ctdir ORIGINAL -j ACCEPT
   sudo iptables -L DOCKER-USER -n -v --line-numbers

   # Keep the rules across reboots
   sudo apt-get install -y iptables-persistent
   sudo netfilter-persistent save

``--ctorigdstport`` matches the port the client connected to, before Docker's DNAT, so the rule
holds even if the container port differs from the host port. ``stack.ps1 doctor`` prints a
reminder when ufw is installed.

.. _deploy-segmentation-network:

How the proxy reaches the segmentation servers
----------------------------------------------

``viking-segmentation`` (Viking ``Servers/SegmentationServer/docker-compose.yml``) has no compose
profiles. Its base service ``segmentation-server`` is the default model behind
``segmentation.<domain>``; every other model is a row of ``Run/viking-segmentation/models.json``,
added with ``stack viking-segmentation model <prefix> <file.pt>`` on the host that runs it. Each
server can be reached in one of three ways:

.. list-table::
   :header-rows: 1
   :widths: 16 42 42

   * - Mode
     - Default server (``segmentation``)
     - ``models.json`` rows (``<prefix>.segmentation``)
   * - Published ports
     - The compose default: host port 40443 (``SEGMENTATION_HTTPS_PORT``), demo page 40444
       (loopback unless ``SEGMENTATION_DEMO_HOST_BIND=0.0.0.0``). The proxy uses
       ``VIKING_COMPUTE_HOST:40443``.
     - ``"network": "published"``, the default when ``VIKING_BACKEND_NETWORK`` is unset: host port
       ``port`` (next free from 40445), reached as ``SEGMENTATION_UPSTREAM_HOST:<port>`` (default
       ``VIKING_COMPUTE_HOST``). Filter these ports with ``DOCKER-USER`` (above).
   * - Own MAC and IP (macvlan)
     - Opt-in with ``STACK_COMPOSE_OVERLAYS=stacks/viking-segmentation/compose.macvlan.yaml`` in the
       run env (Linux, wired NIC, Docker 25 or newer). The server listens on ``<IP>:443`` and
       nothing is published; set ``VIKING_UPSTREAM_SEGMENTATION=<IP>:443`` in the ``viking-proxy``
       run env on ``web``.
     - ``"network": "macvlan"`` with ``mac``, ``ip`` and ``dhcpHostname`` in the row; it shares
       the default server's ``SEGMENTATION_MACVLAN_PARENT`` / ``_LAN_SUBNET`` / ``_LAN_GATEWAY``.
   * - Backend network
     - not used
     - ``"network": "backend"``, the default when ``VIKING_BACKEND_NETWORK`` is set: only when
       ``viking-proxy`` runs on the same host. Nothing is published.

macvlan is how connectomes-deploy's guide for a new segmentation host (``docs/segmentation-host.md``)
sets up the default server. Its run-env block (template: "Own MAC address and IP" in Viking's
``deploy/examples/example.viking-segmentation.run.env``)::

   STACK_COMPOSE_OVERLAYS=stacks/viking-segmentation/compose.macvlan.yaml
   SEGMENTATION_MACVLAN_PARENT=eno1          # or the tagged VLAN sub-interface, e.g. bond0.1811
   SEGMENTATION_LAN_SUBNET=10.20.30.0/24     # CIDR, never a netmask
   SEGMENTATION_LAN_GATEWAY=10.20.30.1
   SEGMENTATION_MAC_ADDRESS=02:5e:10:00:00:01
   SEGMENTATION_LAN_IP=10.20.30.40
   SEGMENTATION_DHCP=1                       # 0 for a static IP without a DHCP client
   SEGMENTATION_DHCP_HOSTNAME=segmentation

The overlay's ``segmentation-net`` container holds the macvlan endpoint and keeps a DHCP lease for
the MAC; ``segmentation-server`` shares its network. What changes compared with published ports:

* Pitt IT reserves the IP for the MAC, lets the switch port carry a second MAC, and opens 443 to
  ``<IP>`` from ``web`` with a network ACL. macvlan traffic bypasses ufw and ``DOCKER-USER``.
* The host itself cannot reach ``<IP>``. Test from ``web``:
  ``openssl s_client -connect <IP>:443 -servername segmentation.<domain>``.
* Restart the pair with ``stack viking-segmentation restart``, never ``segmentation-net`` alone.
  After changing the parent NIC or the subnet, run ``down`` first: an existing network keeps its
  old settings.

The model command writes ``Data/viking-segmentation/proxy-models.map`` and ``cert-names.names``.
On the hosts that run them, they go in ``Data/viking-proxy/models.d/segmentation.map`` (restart
``viking-proxy``) and ``Data/viking-certs/names.d/segmentation.names``; with
``SEGMENTATION_PROXY_MAP_DIR`` and ``SEGMENTATION_CERT_NAMES_DIR`` set the command writes them there
itself. Row fields, TLS and the demo pages: :viking:`Viking segmentation <segmentation.html>`.

SSH keys
--------

On the dev box (Windows OpenSSH client, PowerShell)::

   ssh-keygen -t ed25519 -C "deploy from <your name>"
   type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh deploy@compute.connectomes.pitt.edu "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
   ssh deploy@compute.connectomes.pitt.edu true      # must not prompt for a password

Then turn off password login on each Ubuntu server (the script refuses if ``authorized_keys`` is
empty)::

   sudo bash bootstrap-ubuntu.sh --harden-ssh

Optional ``~/.ssh/config`` aliases make ``targets.psd1`` shorter and work for VS Code too::

   Host compute
       HostName compute.connectomes.pitt.edu
       User deploy
       IdentityFile ~/.ssh/id_ed25519
   Host web
       HostName web.connectomes.pitt.edu
       User deploy

The servers do not need keys on each other: ``stack.ps1 certs push -From web`` runs on the dev
box. Only if you run ``certs push`` on ``web`` itself (for example from cron) does ``web`` need a
key on ``compute`` and ``iis`` and its own ``targets.psd1``.

.. _deploy-windows-openssh:

Windows OpenSSH (``iis``)
~~~~~~~~~~~~~~~~~~~~~~~~~

In an elevated PowerShell on the IIS host (PowerShell 7 must already be installed)::

   Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
   Set-Service sshd -StartupType Automatic
   Start-Service sshd
   New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' -Name DefaultShell -Value 'C:\Program Files\PowerShell\7\pwsh.exe' -PropertyType String -Force

``stack.ps1`` sends PowerShell syntax to Windows targets, so ``DefaultShell`` must be ``pwsh``.
For an account in the Administrators group, keys go in
``C:\ProgramData\ssh\administrators_authorized_keys`` (not the user profile), with an ACL that
only Administrators and SYSTEM can read::

   icacls C:\ProgramData\ssh\administrators_authorized_keys /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"

Set ``PasswordAuthentication no`` in ``C:\ProgramData\ssh\sshd_config`` and
``Restart-Service sshd`` once key login works.

Tunnels
-------

``stack.ps1 tunnel -Target <name>`` opens every forward in that target's ``Tunnels`` list and
holds it until Ctrl+C. The template defines:

.. list-table::
   :header-rows: 1
   :widths: 14 30 56

   * - Target
     - Forward
     - Use
   * - ``compute``
     - ``8087:127.0.0.1:8087``
     - Build dashboard at http://127.0.0.1:8087
   * - ``compute``
     - ``5678:127.0.0.1:5678``
     - debugpy (:doc:`debugging`)
   * - ``web``
     - ``4024:127.0.0.1:4024``
     - Identity .NET remote debugger
   * - ``web``
     - ``1433:<sql-host>:1433``
     - SQL Server as seen from ``web`` (for SSMS / Azure Data Studio on the dev box)

Plain ``ssh -L`` works the same way: ``ssh -N -L 8087:127.0.0.1:8087 deploy@compute.connectomes.pitt.edu``.

VS Code Remote-SSH
------------------

1. Install the **Remote - SSH** and **Dev Containers** extensions.
2. **Remote-SSH: Connect to Host...** ``deploy@compute.connectomes.pitt.edu`` (or the alias), open
   ``/srv/src/nornir`` or ``/srv/docker/Run`` to edit env files in place.
3. To work inside a running container (for example ``nornir-build``): **Dev Containers: Attach to
   Running Container...** from the Remote-SSH window.

Docker contexts
---------------

For quick inspection from the dev box without a shell on the server::

   docker context create compute --docker "host=ssh://deploy@compute.connectomes.pitt.edu"
   docker context create web --docker "host=ssh://deploy@web.connectomes.pitt.edu"
   docker --context compute ps
   docker --context web logs --tail 100 <container>

Use ``stack.ps1 -Target`` for anything that starts or changes a stack: compose bind paths and env
files must resolve on the target, which a context does not do for you.

Tailscale (optional)
--------------------

A Tailscale tailnet gives the dev box a stable private route to ``compute`` and ``web`` without
opening SSH beyond campus. It is a third-party service on university hardware: get Pitt IT's
approval first. With it, point ``Ssh`` in ``targets.psd1`` at the Tailscale host names; nothing
else changes.
