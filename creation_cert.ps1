
$ErrorActionPreference = "Stop"

$caKey = ".\ca.key"
$caCert = ".\nodes\infra\tls\ca.crt"
$outDir = ".\certs"

$nodes = @("node-a", "node-b", "node-c", "api-gateway")

if (!(Test-Path $caKey) -or !(Test-Path $caCert)) {
    throw "ca.key ou ca.crt introuvable."
}

New-Item -ItemType Directory -Force $outDir | Out-Null

foreach ($node in $nodes) {
    $key = "$outDir\$node.key"
    $csr = "$outDir\$node.csr"
    $crt = "$outDir\$node.crt"
    $cnf = "$outDir\$node.cnf"
    $ext = "$outDir\$node.ext"

    @"
[req]
distinguished_name = dn
prompt = no
req_extensions = ext
[dn]
CN = $node
[ext]
subjectAltName = DNS:$node
"@ | Set-Content -Encoding ascii $cnf

    openssl genrsa -out $key 2048
    if ($LASTEXITCODE -ne 0) { throw "Échec de génération de $key" }

    openssl req -new -key $key -out $csr -config $cnf
    if ($LASTEXITCODE -ne 0) { throw "Échec de création du CSR pour $node" }

    @"
subjectAltName=DNS:$node
extendedKeyUsage=serverAuth,clientAuth
"@ | Set-Content -Encoding ascii $ext

    openssl x509 -req -in $csr `
        -CA $caCert -CAkey $caKey -CAcreateserial `
        -days 365 -sha256 -extfile $ext -out $crt

    if ($LASTEXITCODE -ne 0) { throw "Échec de signature pour $node" }

    Write-Host "Certificat créé : $crt"
}
