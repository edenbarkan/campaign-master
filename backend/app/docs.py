import os
from flask import Blueprint, Response, current_app, send_file


docs_bp = Blueprint('docs', __name__)


def _spec_path():
    return os.path.abspath(os.path.join(current_app.root_path, '..', 'openapi.yaml'))


@docs_bp.route('/openapi.yaml')
def openapi_yaml():
    spec_file = _spec_path()
    if not os.path.exists(spec_file):
        return Response('Spec not found', status=404)
    return send_file(spec_file, mimetype='application/yaml')


@docs_bp.route('/docs')
def swagger_ui():
    html = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Campaign Master API Docs</title>
  <link rel=\"stylesheet\" href=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui.css\" />
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; }
    #checklist { padding: 16px 24px; background: #f5f5f5; border-bottom: 1px solid #ddd; }
    #checklist h2 { margin-top: 0; }
    #swagger-container { height: calc(100vh - 180px); }
    #swagger-ui { width: 100%%; height: 100%%; }
  </style>
</head>
<body>
  <div id=\"checklist\">
    <h2>Manual checklist</h2>
    <ol>
      <li>Register + Login &mdash; confirm <code>Set-Cookie: session</code> is returned.</li>
      <li>GET <code>/api/auth/me</code> should return the logged-in user.</li>
      <li>Permission checks: publisher hitting advertiser report returns 403, advertiser hitting publisher report returns 403, no session returns 401.</li>
      <li>Logout and verify <code>/api/auth/me</code> returns 401.</li>
    </ol>
    <p>Use “Try it out” to run requests; the docs share the same origin so session cookies are reused automatically.</p>
  </div>
  <div id=\"swagger-container\">
  <div id=\"swagger-ui\"></div>
  </div>
  <script src=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js\"></script>
  <script>
    window.onload = () => {
      SwaggerUIBundle({
        url: '/openapi.yaml',
        dom_id: '#swagger-ui',
      });
    };
  </script>
</body>
</html>"""
    return Response(html, mimetype='text/html')
