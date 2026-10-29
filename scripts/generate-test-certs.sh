#!/usr/bin/env bash
set -euo pipefail

cert_dir="certs"
ca_key="${cert_dir}/test-ca.key"
ca_cert="${cert_dir}/ca.crt"
ca_config="$(mktemp)"
extensions=""
trap 'rm -f "$ca_config" "$extensions"' EXIT

mkdir -p "$cert_dir"

cat > "$ca_config" <<'EOF'
[req]
distinguished_name=dn
prompt=no
x509_extensions=ca_ext
[dn]
CN=FaceIN test CA
[ca_ext]
basicConstraints=critical,CA:TRUE
keyUsage=critical,keyCertSign,cRLSign
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid:always
EOF

openssl req \
    -x509 \
    -newkey rsa:2048 \
    -sha256 \
    -days 1 \
    -nodes \
    -keyout "$ca_key" \
    -out "$ca_cert" \
    -config "$ca_config"
chmod 600 "$ca_key"

for service in node-a node-b node-c api-gateway; do
    key="${cert_dir}/${service}.key"
    csr="${cert_dir}/${service}.csr"
    cert="${cert_dir}/${service}.crt"
    extensions="$(mktemp)"

    openssl req \
        -new \
        -newkey rsa:2048 \
        -sha256 \
        -nodes \
        -keyout "$key" \
        -out "$csr" \
        -subj "/CN=${service}"
    chmod 600 "$key"

    cat > "$extensions" <<EOF
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth,clientAuth
subjectAltName=DNS:${service}
EOF

    openssl x509 \
        -req \
        -in "$csr" \
        -CA "$ca_cert" \
        -CAkey "$ca_key" \
        -CAcreateserial \
        -days 1 \
        -sha256 \
        -extfile "$extensions" \
        -out "$cert"
    rm -f "$extensions"

    openssl verify \
        -purpose sslserver \
        -verify_hostname "$service" \
        -CAfile "$ca_cert" \
        "$cert"
    openssl verify -purpose sslclient -CAfile "$ca_cert" "$cert"
done