Accounts and tokens
===================

Everything you have to request, buy, or generate before the stacks run. Viking's own list, with the
per-service key names, is :viking:`Viking accounts and tokens <accounts_and_tokens.html>`. Secrets go only in
``Run/_host/secrets/secrets.env``, ``Run/<stack>/secrets/``, or ``Run/nornir-net-mounts/secrets/``
on the host that needs them (:doc:`host_layout`). Never commit them, paste them in tickets, or put
them in ``host.env`` or ``<stack>.run.env``.

External accounts and requests
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 18 22 24 20 16

   * - Item
     - Where to get it
     - What it is / scope
     - Where it goes
     - Needed for
   * - GitHub fine-grained PAT (servers)
     - github.com > Settings > Developer settings > Personal access tokens > Fine-grained
     - Packages: read. Contents: read on ``jamesra/nornir`` and ``jamesra/Viking`` only if they
       are private. Short expiry; one token per host.
     - ``Run/_host/secrets/secrets.env`` (``GITHUB_TOKEN``); then once per host
       ``docker login ghcr.io -u <github-user>`` with the token as password
     - ``-Images ghcr``, ``stack.ps1 nornir-build pull``, private clones
   * - GitHub fine-grained PAT (dev box)
     - same
     - Packages: read and write (``docker-push.ps1``); Contents: read/write if you push over HTTPS
     - dev box ``Run/_host/secrets/secrets.env``; ``docker login ghcr.io``
     - publishing images
   * - DNS record
     - Pitt IT ticket
     - Wildcard ``*.connectomes.pitt.edu`` (or one record per name) to the ``web`` server's
       public address
     - Pitt DNS
     - every public name; ``doctor`` checks resolution
   * - Firewall rules
     - Pitt IT ticket
     - The per-host table in :ref:`deploy-firewall-request`
     - Pitt network firewall
     - public access, cross-host traffic
   * - Certificate, or ACME EAB credentials
     - Pitt IT ticket (InCommon / Sectigo)
     - Either a wildcard/SAN certificate with its key and intermediate chain, or an ACME EAB key id
       (KID), HMAC key, and the ACME server URL
     - Certificate files: ``stack.ps1 certs manual``. EAB: ``TLS_EAB_KID`` and
       ``TLS_EAB_HMAC_KEY`` in ``Run/viking-certs/secrets/secrets.env`` on ``web``; URL as
       ``TLS_ACME_SERVER``
     - ``TLS_MODE=manual`` or ``acme-eab`` (when Let's Encrypt or port 80 is not allowed)
   * - Let's Encrypt
     - nothing to request
     - Only a contact email; no account, token, or payment
     - ``TLS_EMAIL`` in ``host.env``
     - ``TLS_MODE=letsencrypt``
   * - Duende IdentityServer license
     - duendesoftware.com (purchase or community license)
     - License key file for the IdentityServer edition in use
     - ``Run/viking-identity/secrets/Duende_License.key`` on ``web``
     - ``viking-identity`` in production
   * - Pitt SMTP credentials
     - Pitt IT
     - Relay host, port, user, and password for outgoing mail
     - ``Run/viking-identity/secrets/`` (key names in the Viking identity template)
     - Identity email (password reset, confirmations)
   * - SQL Server logins
     - SQL Server DBA (or Pitt IT)
     - One login per service with rights on its databases only
     - ``SQL_SERVER_*`` / ``ConnectionStrings__*`` in the Viking stack's ``secrets/secrets.env``
     - ``viking-identity``, ``viking-annotation``, ``viking-iis``
   * - NAS share account
     - lab storage administrator
     - SMB user that can read (and write, for builds) the volume shares
     - ``Run/nornir-net-mounts/secrets/net-creds/<id>.cred`` on ``compute``
     - ``nornir-build`` CIFS mounts
   * - Cursor API key (optional)
     - cursor.com > settings
     - Key for the self-hosted agent worker
     - ``Run/nornir-cursor-worker/nornir-cursor-worker.run.env`` (``CURSOR_API_KEY``)
     - ``nornir-cursor-worker``
   * - Slack bot token (optional)
     - api.slack.com > Your apps > OAuth & Permissions
     - Bot token (``xoxb-...``) for notifications
     - the consuming stack's ``secrets/secrets.env`` (``SLACK_BOT_TOKEN``)
     - optional notifications
   * - ``NORNIR_ORG_GITHUB_IO_DEPLOY_TOKEN``
     - GitHub PAT with write access to ``nornir/nornir.github.io``
     - GitHub Actions repository secret on ``jamesra/nornir``, not a host file
     - repo Settings > Secrets and variables > Actions
     - publishing these docs (:doc:`../development/publishing_documentation`)
   * - YubiKey code-signing certificate
     - unchanged from the existing release process
     - Hardware-held code-signing certificate
     - the YubiKey; never on a server
     - signing Viking client releases

Generated secrets
-----------------

These are random values you create, not accounts. ``stack.ps1 secrets new <stack> [KEY ...]``
writes a 32-byte URL-safe random value for the stack's registry-listed ``*_SECRET``, ``*_TOKEN``
and ``*_PASSWORD`` keys, for any key still holding a ``REPLACE_WITH_GENERATED...`` placeholder,
and for any key you name. It replaces the placeholder where it is (``secrets/secrets.env``, else
``<stack>.run.env``) or appends to ``secrets/secrets.env``. Keys that already have a value are
kept, so it is safe to re-run; ``stack.ps1 doctor`` treats ``REPLACE_ME`` / ``REPLACE_WITH_...``
values as empty. ``*_PASSWORD`` values get an ``Aa1!`` prefix to satisfy SQL Server complexity
rules. ``SQL_SERVER_PASSWORD`` and connection strings are never generated (they belong to existing
SQL logins). Empty optional client secrets are left alone, because empty means that client is
disabled: name the ones you want, for example
``stack.ps1 secrets new viking-identity CORRECTION_SERVICE_CLIENT_SECRET``.

.. list-table::
   :header-rows: 1
   :widths: 36 22 42

   * - Key
     - Generate in
     - Also copy to
   * - ``IDENTITY_SERVER_SECRET``, ``IDENTITY_SERVER_API_SECRET``, ``IDENTITY_SERVER_MVC_SECRET``,
       ``IDENTITY_SERVER_RO_VIKING_SECRET``
     - ``viking-identity``
     - the clients that use them (:viking:`Viking accounts and tokens <accounts_and_tokens.html>`)
   * - ``CORRECTION_SERVICE_CLIENT_SECRET``
     - ``viking-identity``
     - ``viking-corrections`` as ``IdentityServer__ClientSecret``
   * - ``GALLERY_*_CLIENT_SECRET``
     - ``viking-identity``
     - the gallery's env in the Sam2Trainer repository (not a ``stack.ps1`` stack)
   * - ``SBFSEM_TOOLS_CLIENT_SECRET``
     - ``viking-identity``
     - SBFSEM-tools configuration
   * - ``NORNIR_DASHBOARD_TOKEN``
     - ``nornir-dashboard``
     - your browser (``http://127.0.0.1:8087/?token=...``), only when the bind host is widened
   * - ``SEGMENTATION_DEMO_TOKEN``
     - ``viking-segmentation``
     - people given the demo page
   * - ``MSSQL_SA_PASSWORD``
     - ``viking-annotation`` (``local-sql`` profile only)
     - nothing; production uses the external SQL Server

Rotate a value by deleting its line and re-running ``secrets new``, then update every consumer
and ``stack.ps1 <stack> restart`` each one.
