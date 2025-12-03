package server

import (
	"fmt"
	"html/template"
	"io/fs"
	"log"
	"net/http"
	"path/filepath"
	"strings"
	"time"

	"homepage/internal/config"
	"homepage/internal/service"
)

type Server struct {
	mux     *http.ServeMux
	content fs.FS
}

func New(content fs.FS) *Server {
	s := &Server{
		mux:     http.NewServeMux(),
		content: content,
	}
	s.routes()
	return s
}

func (s *Server) routes() {
	s.mux.HandleFunc("GET /", s.handleIndex)
	s.mux.HandleFunc("GET /favicon/{id}", s.handleFavicon)
	s.mux.HandleFunc("GET /download/{path...}", s.handleDownload)

	// Static files
	staticFS, err := fs.Sub(s.content, "static")
	if err != nil {
		log.Fatal(err)
	}
	fileServer := http.FileServer(http.FS(staticFS))
	s.mux.Handle("GET /static/", http.StripPrefix("/static/", fileServer))

	// Catch-all for service redirection
	// Note: In Go 1.22, we can't easily have a catch-all that doesn't conflict with specific paths
	// if we want it to be at root level but not match /static or /favicon.
	// However, since we defined specific paths above, we can use a pattern that matches everything else?
	// Actually, "GET /" matches everything not matched by others.
	// But we want "GET /" to be index, and "GET /foo" to be redirect.
	// So we handle both in handleIndex or use a middleware/custom handler.
	// Let's use a custom handler for the root to dispatch.
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// Custom dispatch logic to handle "GET /" vs "GET /service"
	if r.URL.Path == "/" {
		s.handleIndex(w, r)
		return
	}

	// Check if it matches other registered routes
	// This is a bit tricky with standard mux if we want to intercept.
	// Alternative: Register "/" and check path inside.

	// Let's try registering "/" and doing the logic there.
	// But wait, s.mux.Handle("GET /static/") works.
	// If I register "GET /", it matches everything.
	// So I should register specific routes, and then "GET /" as the catch-all.
	// Inside "GET /", if path is "/", serve index.
	// If path is "/something", try to redirect.

	s.mux.ServeHTTP(w, r)
}

func (s *Server) handleIndex(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		// This is likely a service redirect request
		serviceName := strings.TrimPrefix(r.URL.Path, "/")
		s.handleRedirect(w, r, serviceName)
		return
	}

	cfg := config.Get()
	downloads, err := service.GetDownloadableFiles()
	if err != nil {
		log.Printf("Error getting downloads: %v", err)
	}

	data := struct {
		SiteTitle     string
		Services      map[string]config.ServiceInfo
		Downloads     map[string][]service.FileInfo
		DefaultDomain string
		Now           func() time.Time
	}{
		SiteTitle:     cfg.SiteTitle,
		Services:      cfg.Services,
		Downloads:     downloads,
		DefaultDomain: cfg.DefaultDomain,
		Now:           time.Now,
	}

	tmpl, err := template.New("index.html").Funcs(template.FuncMap{
		"now": time.Now,
		"date": func(layout string, t time.Time) string {
			return t.Format(layout)
		},
	}).ParseFS(s.content, "templates/index.html")

	if err != nil {
		http.Error(w, "Template error: "+err.Error(), http.StatusInternalServerError)
		return
	}

	if err := tmpl.Execute(w, data); err != nil {
		log.Printf("Template execution error: %v", err)
	}
}

func (s *Server) handleRedirect(w http.ResponseWriter, r *http.Request, serviceID string) {
	cfg := config.Get()
	if svc, ok := cfg.Services[serviceID]; ok {
		domain := svc.Domain
		if domain == "" {
			domain = cfg.DefaultDomain
		}
		target := fmt.Sprintf("http://%s:%d", domain, svc.Port)
		http.Redirect(w, r, target, http.StatusFound)
		return
	}
	http.NotFound(w, r)
}

func (s *Server) handleFavicon(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	cfg := config.Get()

	svc, ok := cfg.Services[id]
	if !ok || svc.Favicon == "" {
		http.NotFound(w, r)
		return
	}

	faviconPath := filepath.Join("favicons", svc.Favicon)
	http.ServeFile(w, r, faviconPath)
}

func (s *Server) handleDownload(w http.ResponseWriter, r *http.Request) {
	path := r.PathValue("path")
	fullPath := filepath.Join(service.FilesPath, path)

	// Security check: prevent directory traversal
	// filepath.Join cleans the path, but let's be safe
	if !strings.HasPrefix(filepath.Clean(fullPath), service.FilesPath) {
		http.NotFound(w, r)
		return
	}

	w.Header().Set("Content-Disposition", "attachment; filename="+filepath.Base(path))
	http.ServeFile(w, r, fullPath)
}

func (s *Server) Run(port int) error {
	addr := fmt.Sprintf(":%d", port)
	log.Printf("Starting server on %s", addr)
	return http.ListenAndServe(addr, s)
}
