package service

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

var FilesPath = "files"

func init() {
	os.MkdirAll(FilesPath, 0755)
}

type FileInfo struct {
	Name          string `json:"name"`
	Filename      string `json:"filename"`
	Size          int64  `json:"size"`
	FormattedSize string `json:"formatted_size"`
	Icon          string `json:"icon"`
	UploadTime    string `json:"upload_time"`
	Description   string `json:"description"`
}

func FormatSize(size int64) string {
	s := float64(size)
	units := []string{"B", "KB", "MB", "GB"}
	for _, unit := range units {
		if s < 1024 {
			return fmt.Sprintf("%.1f %s", s, unit)
		}
		s /= 1024
	}
	return fmt.Sprintf("%.1f TB", s)
}

func GetFileIcon(filename string) string {
	ext := strings.ToLower(filepath.Ext(filename))
	iconGroups := map[string][]string{
		"file-zipper":     {".zip", ".rar", ".7z"},
		"box":             {".tar", ".xz", ".gz"},
		"file-pdf":        {".pdf"},
		"file-word":       {".doc", ".docx"},
		"file-excel":      {".xls", ".xlsx"},
		"file-powerpoint": {".ppt", ".pptx"},
		"file-lines":      {".txt"},
		"book":            {".md"},
		"file-image":      {".jpg", ".jpeg", ".png", ".gif", "bmp"},
		"file-audio":      {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"},
		"file-video":      {".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv", ".webm"},
		"cube":            {".exe", ".bin", ".jar"},
		"file-code":       {".py", ".c", ".cpp", ".java", ".html", ".css", ".js", ".go"},
		"terminal":        {".sh", ".bat"},
		"database":        {".accdb", ".db", ".sql", ".sqlite"},
	}

	for icon, exts := range iconGroups {
		for _, e := range exts {
			if e == ext {
				return icon
			}
		}
	}
	return "file"
}

func GetDownloadableFiles() (map[string][]FileInfo, error) {
	categories := make(map[string][]FileInfo)
	
	// Load descriptions
	descriptions := make(map[string]string)
	descFile := filepath.Join(FilesPath, "descriptions.json")
	if data, err := os.ReadFile(descFile); err == nil {
		json.Unmarshal(data, &descriptions)
	}

	if _, err := os.Stat(FilesPath); os.IsNotExist(err) {
		return categories, nil
	}

	err := filepath.Walk(FilesPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() {
			return nil
		}
		if info.Name() == "descriptions.json" || strings.HasSuffix(info.Name(), ".part") {
			return nil
		}

		relPath, err := filepath.Rel(FilesPath, path)
		if err != nil {
			return err
		}

		dir := filepath.Dir(relPath)
		category := "未分类"
		if dir != "." {
			category = strings.ReplaceAll(dir, string(os.PathSeparator), " / ")
		}

		fileInfo := FileInfo{
			Name:          info.Name(),
			Filename:      filepath.ToSlash(relPath), // Ensure forward slashes for URLs
			Size:          info.Size(),
			FormattedSize: FormatSize(info.Size()),
			Icon:          GetFileIcon(info.Name()),
			UploadTime:    info.ModTime().Format("2006-01-02 15:04"),
			Description:   descriptions[info.Name()],
		}
		
		if fileInfo.Description == "" {
			ext := strings.ToUpper(strings.TrimPrefix(filepath.Ext(info.Name()), "."))
			fileInfo.Description = ext + "文件"
		}

		categories[category] = append(categories[category], fileInfo)
		return nil
	})

	// Sort files within categories
	for cat := range categories {
		sort.Slice(categories[cat], func(i, j int) bool {
			return categories[cat][i].Name < categories[cat][j].Name
		})
	}
	
	// Sort "未分类" by time desc if it exists (matching Python logic)
	if files, ok := categories["未分类"]; ok {
		sort.Slice(files, func(i, j int) bool {
			// Parse time back for sorting or just use modtime if we stored it. 
			// For simplicity, let's just sort by name for now or keep it simple.
			// Python code sorts root files by upload time desc.
			// Let's try to match that.
			t1, _ := time.Parse("2006-01-02 15:04", files[i].UploadTime)
			t2, _ := time.Parse("2006-01-02 15:04", files[j].UploadTime)
			return t1.After(t2)
		})
	}

	return categories, err
}
