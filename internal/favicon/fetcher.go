package favicon

import (
	"crypto/tls"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"homepage/internal/config"
)

var (
	FaviconDir = "favicons"
)

func init() {
	os.MkdirAll(FaviconDir, 0755)
}

func getServiceURL(port int, domain, defaultDomain string) string {
	d := domain
	if d == "" {
		d = defaultDomain
	}
	scheme := "http"
	if port == 443 {
		scheme = "https"
	}
	return fmt.Sprintf("%s://%s:%d", scheme, d, port)
}

func fetchFavicon(serviceID string, info config.ServiceInfo, defaultDomain string) (string, error) {
	// Check if already exists
	matches, _ := filepath.Glob(filepath.Join(FaviconDir, serviceID+".*"))
	if len(matches) > 0 {
		return filepath.Base(matches[0]), nil
	}

	baseURL := getServiceURL(info.Port, info.Domain, defaultDomain)
	paths := []string{
		"/static/favicon.ico",
		"/images/favicon.ico",
		"/img/favicon.ico",
		"/assets/favicon.ico",
		"/favicon.ico",
		"/favicon.png",
		"/favicon.jpg",
		"/favicon.svg",
	}

	client := &http.Client{
		Timeout: 15 * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		},
	}

	for _, path := range paths {
		targetURL, err := url.JoinPath(baseURL, path)
		if err != nil {
			continue
		}

		resp, err := client.Get(targetURL)
		if err != nil {
			continue
		}
		defer resp.Body.Close()

		if resp.StatusCode == 200 {
			contentType := resp.Header.Get("Content-Type")
			ext := "ico"
			if strings.Contains(contentType, "image/png") || strings.HasSuffix(targetURL, ".png") {
				ext = "png"
			} else if strings.Contains(contentType, "image/jpeg") || strings.HasSuffix(targetURL, ".jpg") || strings.HasSuffix(targetURL, ".jpeg") {
				ext = "jpg"
			} else if strings.Contains(contentType, "image/svg+xml") || strings.HasSuffix(targetURL, ".svg") {
				ext = "svg"
			}

			filename := fmt.Sprintf("%s.%s", serviceID, ext)
			filepath := filepath.Join(FaviconDir, filename)
			
			out, err := os.Create(filepath)
			if err != nil {
				return "", err
			}
			defer out.Close()

			_, err = io.Copy(out, resp.Body)
			if err != nil {
				return "", err
			}

			return filename, nil
		}
	}

	return "", fmt.Errorf("favicon not found")
}

func Refresh() {
	cfg := config.Get()
	var wg sync.WaitGroup
	sem := make(chan struct{}, 5) // Max 5 concurrent

	updated := false
	var mu sync.Mutex

	for id, info := range cfg.Services {
		wg.Add(1)
		go func(id string, info config.ServiceInfo) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			filename, err := fetchFavicon(id, info, cfg.DefaultDomain)
			if err == nil && filename != "" && info.Favicon != filename {
				mu.Lock()
				// Need to update the map in the config safely
				// But we are iterating over it? No, we are iterating a copy or range?
				// Range over map is safe for concurrent read if map is not modified.
				// But we want to modify it.
				// Better to collect updates and apply them later.
				// Or use the config's mutex if we exposed it, but we didn't expose SetFavicon.
				// Let's just update a local copy or use a setter.
				// For now, let's assume we can modify the entry if we are careful.
				// Actually, config.Get() returns a pointer to the global config.
				// We should probably add a method to Config to update a service.
				
				// Let's just log for now and update later?
				// No, we want to save it.
				// Let's use a temporary map for updates.
				updated = true
				// We can't modify cfg.Services[id] directly because it's a value (struct), not pointer?
				// Wait, map values are not addressable.
				// So:
				entry := cfg.Services[id]
				entry.Favicon = filename
				cfg.Services[id] = entry
				mu.Unlock()
				log.Printf("Fetched favicon for %s: %s", id, filename)
			}
		}(id, info)
	}
	wg.Wait()

	if updated {
		if err := cfg.Save(); err != nil {
			log.Printf("Error saving config after favicon refresh: %v", err)
		}
	}
}

func Clear() {
	files, _ := filepath.Glob(filepath.Join(FaviconDir, "*"))
	for _, f := range files {
		os.Remove(f)
	}
	
	cfg := config.Get()
	for id, info := range cfg.Services {
		info.Favicon = ""
		cfg.Services[id] = info
	}
	cfg.Save()
}
