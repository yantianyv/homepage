package config

import (
	"encoding/json"
	"os"
	"strings"
	"sync"
)

type ServiceInfo struct {
	Name    string `json:"name"`
	Port    int    `json:"port"`
	Domain  string `json:"domain,omitempty"`
	Favicon string `json:"favicon,omitempty"`
}

func (s ServiceInfo) IsLocal() bool {
	if s.Domain == "" {
		return false
	}
	return s.Domain == "localhost" ||
		strings.HasPrefix(s.Domain, "10.") ||
		strings.HasPrefix(s.Domain, "127.") ||
		strings.HasPrefix(s.Domain, "192.")
}

type Config struct {
	Services      map[string]ServiceInfo `json:"services"`
	DefaultDomain string                 `json:"default_domain"`
	SiteTitle     string                 `json:"site_title"`
	Shutdown      bool                   `json:"shutdown"`
	mu            sync.RWMutex
}

var (
	GlobalConfig *Config
	ConfigPath   = "config.json"
)

func Load() error {
	f, err := os.Open(ConfigPath)
	if err != nil {
		return err
	}
	defer f.Close()

	var cfg Config
	if err := json.NewDecoder(f).Decode(&cfg); err != nil {
		return err
	}

	if cfg.DefaultDomain == "" {
		cfg.DefaultDomain = "127.0.0.1"
	}
	if cfg.SiteTitle == "" {
		cfg.SiteTitle = "Service Navigation Center"
	}

	GlobalConfig = &cfg
	return nil
}

func Get() *Config {
	if GlobalConfig == nil {
		GlobalConfig = &Config{
			Services:      make(map[string]ServiceInfo),
			DefaultDomain: "127.0.0.1",
		}
	}
	return GlobalConfig
}

func (c *Config) Save() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	f, err := os.Create(ConfigPath)
	if err != nil {
		return err
	}
	defer f.Close()

	encoder := json.NewEncoder(f)
	encoder.SetIndent("", "    ")
	return encoder.Encode(c)
}
