admin = """
<!doctype html>
<html lang="en">
<head>
<title>Library Registry</title>
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<link href=\"/admin/static/registry-admin.css\" rel="stylesheet" />
</head>
<body>
  <script src=\"/admin/static/registry-admin.js\"></script>
  <script>
    var registryAdmin = new RegistryAdmin({username: \"{{ username }}\"});
  </script>
  <h1></h1>
</body>
</html>
"""
