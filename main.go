package main

import (
	"embed"
	"flag"
	"fmt"
	"log"
	"os"
	"time"

	"homepage/internal/cli"
	"homepage/internal/config"
	"homepage/internal/favicon"
	"homepage/internal/server"
)

//go:embed templates static
var content embed.FS

func main() {
	port := flag.Int("port", 80, "Port to run the server on")
	shutdown := flag.Bool("shutdown", false, "Shutdown the server")
	setup := flag.Bool("s", false, "Open configuration menu") // -s flag
	flag.Parse()

	if *setup {
		cli.MainMenu()
		return
	}

	if *shutdown {
		fmt.Println("Shutdown flag received. Exiting.")
		os.Exit(0)
	}

	if err := config.Load(); err != nil {
		fmt.Printf("Config not found or invalid: %v. Launching setup...\n", err)
		cli.MainMenu()
		// Reload after setup
		if err := config.Load(); err != nil {
			log.Printf("Warning: Could not load config after setup: %v", err)
		}
	}

	// Background tasks
	go func() {
		// Initial favicon refresh
		favicon.Refresh()

		for {
			time.Sleep(60 * time.Second)

			// Refresh config
			if err := config.Load(); err != nil {
				log.Printf("Error reloading config: %v", err)
			}
			if config.Get().Shutdown {
				log.Println("Shutdown requested via config")
				os.Exit(0)
			}

			// Refresh favicons
			favicon.Refresh()
		}
	}()

	srv := server.New(content)
	if err := srv.Run(*port); err != nil {
		log.Fatal(err)
	}
}
