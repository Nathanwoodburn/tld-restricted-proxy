# TLD Restricted Proxy

Environment variables:
- `PROXY` - The proxy to use for restricted TLDs. Example: `http://localhost:3128`
- `TLD` - The TLD to restrict. Example: `g`
- `RESTRICTED` - List of restricted paths. Example: `["path1", "path2"]` will require the user to have a .g domain to access `path1/*`, `path2/*`

