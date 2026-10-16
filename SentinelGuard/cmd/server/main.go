package main

import (
	"log"
	"net/http"
	"os"
	"strings"

	"sentinelguard/server"
)

func main() {
	cfg := server.LoadServerConfigFromEnv()

	store, err := server.NewStoreFromConfig(cfg)
	if err != nil {
		log.Fatalf("store init: %v", err)
	}

	r := server.Router(store, cfg.Router, cfg.Embedding)
	addr := getenv("SERVER_ADDR", ":8085")

	log.Printf("sentinelguard server listening on %s (store=%s index=%s)", addr, strings.ToLower(cfg.StoreKind), cfg.OpenSearch.Index)
	if err := http.ListenAndServe(addr, r); err != nil {
		log.Fatal(err)
	}
}

func getenv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}
