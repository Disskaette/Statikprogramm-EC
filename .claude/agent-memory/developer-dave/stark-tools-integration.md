# stark-tools Integration Details

## Location
`/Users/maximilianstark/Library/Mobile Documents/com~apple~CloudDocs/Dokumente/Programmierzeug/stark-tools/`

## Auth System
- Flask-based, cookie sessions (`stark_session`)
- SQLite at `/data/sessions.db`
- nginx `auth_request /internal/auth` subrequest pattern
- Users: stark(mitarbeiter), admin(admin), felix_k(felix)

## Integration Pattern (3 places to modify)
1. `docker-compose.yml` - add service definition
2. `nginx.conf` - add location block with auth_request
3. `auth/app.py` - add to KACHELN list with roles

## Statik Tool Access
- URL: `/statik/`
- Roles: `["admin", "felix"]`
- Port: 8000 (FastAPI, not Streamlit)
- WebSocket upgrade headers needed for future features

## Existing Tools
- holzlisten: port 8501, route /holzlisten/
- sortierprozess: port 8502, route /joerg/
