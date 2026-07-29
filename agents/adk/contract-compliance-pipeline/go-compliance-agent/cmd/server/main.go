package main

import (
	"context"
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"go-compliance-agent/internal/agentcard"
	"go-compliance-agent/internal/handler"
)

func main() {
	// Parse CLI parameters
	port := flag.String("port", "8888", "Go A2A Service listener port")
	policyPath := flag.String("policy", "internal/policies/default_policy.json", "Compliance rules JSON file path")
	flag.Parse()

	fmt.Println("--- Go Compliance Agent (A2A Protocol) ---")
	fmt.Printf("Bootstrapping validation policies from %s\n", *policyPath)
	handler.InitPolicies(*policyPath)

	// API Routing definition — A2A uses a single JSON-RPC endpoint at root.
	// The agent card endpoint must be registered first so it takes priority.
	mux := http.NewServeMux()
	mux.HandleFunc("/.well-known/agent.json", agentcard.Handler)
	mux.HandleFunc("/", handler.HandleJSONRPC)

	// Global Middleware enabling CORS checks
	corsHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Accept")

		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusOK)
			return
		}
		mux.ServeHTTP(w, r)
	})

	// Bind address — configurable via HOST env var, defaults to 0.0.0.0 for container compatibility
	host := os.Getenv("HOST")
	if host == "" {
		host = "0.0.0.0"
	}
	bindAddr := net.JoinHostPort(host, *port)

	server := &http.Server{
		Addr:    bindAddr,
		Handler: corsHandler,
	}

	// Graceful shutdown listeners
	idleConnsClosed := make(chan struct{})
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
		<-sigChan

		fmt.Println("\nReceived termination signal. Shutting down A2A service gracefully...")
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		if err := server.Shutdown(ctx); err != nil {
			fmt.Printf("Error shutting down server: %v\n", err)
		}
		close(idleConnsClosed)
	}()

	fmt.Printf("Agent Card:  http://%s/.well-known/agent.json\n", bindAddr)
	fmt.Printf("JSON-RPC:    http://%s/\n", bindAddr)
	fmt.Printf("A2A compliance validation engine listening on %s...\n", bindAddr)

	if err := server.ListenAndServe(); err != http.ErrServerClosed {
		fmt.Printf("Error starting server: %v\n", err)
		os.Exit(1)
	}

	<-idleConnsClosed
	fmt.Println("Security validation service exited safely.")
}
