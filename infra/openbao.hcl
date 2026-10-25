ui = false
api_addr = "http://openbao:8200"
cluster_addr = "https://openbao:8201"
storage "raft" {
  path = "/bao/data"
  node_id = "bmdl-1"
}
listener "tcp" {
  address = "0.0.0.0:8200"
  tls_disable = true
}
