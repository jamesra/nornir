# RC2 Grid32 refine fixtures (Manual Leveled)

Imported into `D:/nornir-testdata/refine_fixtures/RC2/Grid32/` from
`Y:/Volumes/RC2/TEM/Grid32` (**Leveled only**, no Blob).

| Pair (on disk) | Confirmed tags | Manual gold | Notes |
|----------------|----------------|-------------|-------|
| 654-653 | tear | no | Tear / missing chunk; Automatic only |
| 704-702 | tear | yes | User asked 702-704; volume stores **704-702** |
| 702-701 | dirt | yes | |
| 710-708 | dirt | yes | |
| 728-727 | contrast-mismatch | yes | |
| 772-771 | white-stripe | yes | |
| 792-791 | tear, fold | yes | Very challenging; also suggested `high-relative-distortion` |
| 818-816 | white-stripe | yes | |
| 833-832 | tear | yes | Tear / missing chunk |
| 848-847 | fold | yes | User asked 848-846; **no such pair** — closest Manual is **848-847** |
| 850-849 | tear | no | Tear / missing chunks; Automatic only |
| 590-591 | healthy | no | Should work |
| 605-606 | healthy, white-stripe | no | Healthy with minor white stripe |

Catalog: `D:/nornir-testdata/refine_fixtures/catalog.sqlite`

Importer CuPy fix: `EnsureNumpyArray` in strain picker / crop shift (host boundary for metrics).
