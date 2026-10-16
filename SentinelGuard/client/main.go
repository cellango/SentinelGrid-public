package main

import (
	"context"
	"log"

	"sentinelguard/agent"
)

func main() {
	cfg := agent.FromEnv()
	ag, err := agent.NewAgent(cfg)
	if err != nil {
		log.Fatalf("init agent: %v", err)
	}

	ctx := context.Background()
	if err := ag.Run(ctx); err != nil {
		log.Fatalf("run agent: %v", err)
	}
	log.Printf("sentinelguard agent finished run; tenant=%s agent=%s", cfg.TenantID, cfg.AgentID)
}
