#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "${script_dir}/.." && pwd)"
ca_key="${project_root}/ca.key"
ca_cert="${project_root}/nodes/infra/tls/ca.crt"
out_dir="${project_root}/certs"

nodes=(node-a node-b node-c api-gateway)

if [[ ! -f "$ca_key" || ! -f "$ca_cert" ]]; then
    printf 'ca.key ou ca.crt introuvable.\n' >&2
    exit 1
fi

mkdir -p "$out_dir"

for node in "${nodes[@]}"; do
    key="${out_dir}/${node}.key"
    csr="${out_dir}/${node}.csr"
    crt="${out_dir}/${node}.crt"
    cnf="${out_dir}/${node}.cnf"
    ext="${out_dir}/${node}.ext"

    cat > "$cnf" <<EOF
[req]
distinguished_name = dn
prompt = no
req_extensions = ext
[dn]
CN = ${node}
[ext]
subjectAltName = DNS:${node}
EOF

    if ! openssl genrsa -out "$key" 2048; then
        printf 'Échec de génération de %s\n' "$key" >&2
        exit 1
    fi

    if ! openssl req -new -key "$key" -out "$csr" -config "$cnf"; then
        printf 'Échec de création du CSR pour %s\n' "$node" >&2
        exit 1
    fi

    cat > "$ext" <<EOF
subjectAltName=DNS:${node}
extendedKeyUsage=serverAuth,clientAuth
EOF

    if ! openssl x509 -req -in "$csr" \
        -CA "$ca_cert" -CAkey "$ca_key" -CAcreateserial \
        -days 365 -sha256 -extfile "$ext" -out "$crt"; then
        printf 'Échec de signature pour %s\n' "$node" >&2
        exit 1
    fi

    printf 'Certificat créé : %s\n' "$crt"
done
