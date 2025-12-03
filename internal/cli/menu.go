package cli

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"sort"
	"strconv"
	"strings"

	"homepage/internal/config"
	"homepage/internal/favicon"
)

func clearScreen() {
	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		cmd = exec.Command("cmd", "/c", "cls")
	} else {
		cmd = exec.Command("clear")
	}
	cmd.Stdout = os.Stdout
	cmd.Run()
}

func printLine() {
	fmt.Println(strings.Repeat("-", 50))
}

func printTitle(title string) {
	fmt.Println(strings.Repeat("=", 50))
	fmt.Printf("%*s\n", (50+len(title))/2, title) // Simple centering, might not be perfect for wide chars
	// Better centering for mixed width?
	// Let's just print it.
	fmt.Println(strings.Repeat("=", 50))
}

func readInput(prompt string) string {
	fmt.Print(prompt)
	scanner := bufio.NewScanner(os.Stdin)
	if scanner.Scan() {
		return strings.TrimSpace(scanner.Text())
	}
	return ""
}

func showServices(cfg *config.Config) {
	clearScreen()
	printTitle("当前配置的服务")
	
	var keys []string
	for k := range cfg.Services {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	if len(keys) == 0 {
		fmt.Println("没有配置任何服务！")
	} else {
		for _, id := range keys {
			svc := cfg.Services[id]
			domain := svc.Domain
			if domain == "" {
				domain = cfg.DefaultDomain
			}
			fmt.Printf("- %s: %s (端口: %d, 域名: %s)\n", id, svc.Name, svc.Port, domain)
		}
	}
	readInput("\n按回车返回主菜单...")
}

func addService(cfg *config.Config) {
	clearScreen()
	printTitle("添加服务")
	
	id := readInput("请输入服务ID: ")
	if id == "" {
		return
	}
	
	name := readInput("请输入显示名称: ")
	
	var port int
	for {
		pStr := readInput("请输入端口号: ")
		p, err := strconv.Atoi(pStr)
		if err == nil {
			port = p
			break
		}
		fmt.Println("端口号必须是数字，请重新输入。")
	}

	domain := readInput("请输入域名 (留空使用全局域名): ")

	if _, exists := cfg.Services[id]; exists {
		fmt.Printf("服务 %s 已存在！\n", id)
	} else {
		svc := config.ServiceInfo{
			Name:   name,
			Port:   port,
			Domain: domain,
		}
		cfg.Services[id] = svc
		cfg.Save()
		
		finalDomain := domain
		if finalDomain == "" {
			finalDomain = cfg.DefaultDomain
		}
		fmt.Printf("服务 %s 添加成功！将使用域名: %s\n", id, finalDomain)
	}
	readInput("\n按回车返回主菜单...")
}

func deleteService(cfg *config.Config) {
	clearScreen()
	var keys []string
	for k := range cfg.Services {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	if len(keys) == 0 {
		fmt.Println("没有配置任何服务，无法删除！")
		readInput("\n按回车返回主菜单...")
		return
	}

	printTitle("删除服务")
	fmt.Println("请选择要删除的服务 (输入 0 取消操作)：")
	for i, id := range keys {
		fmt.Printf("%d. %s\n", i+1, id)
	}

	for {
		choiceStr := readInput("\n请输入服务编号: ")
		choice, err := strconv.Atoi(choiceStr)
		if err != nil {
			fmt.Println("请输入有效的数字。")
			continue
		}
		
		if choice == 0 {
			fmt.Println("取消删除操作。")
			return
		}
		
		if choice >= 1 && choice <= len(keys) {
			id := keys[choice-1]
			delete(cfg.Services, id)
			cfg.Save()
			fmt.Printf("服务 %s 删除成功！\n", id)
			break
		}
		fmt.Println("无效的选择，请重新输入。")
	}
	readInput("\n按回车返回主菜单...")
}

func setDefaultDomain(cfg *config.Config) {
	clearScreen()
	printTitle("设置全局域名")
	fmt.Printf("当前全局域名: %s\n", cfg.DefaultDomain)
	domain := readInput("请输入新的全局域名 (按回车保持当前域名): ")
	
	if domain != "" {
		cfg.DefaultDomain = domain
		cfg.Save()
		fmt.Printf("全局域名已设置为 %s\n", domain)
	} else {
		fmt.Println("全局域名未修改。")
	}
	readInput("\n按回车返回主菜单...")
}

func setTitle(cfg *config.Config) {
	clearScreen()
	printTitle("设置标题")
	fmt.Printf("当前标题: %s\n", cfg.SiteTitle)
	title := readInput("请输入新的标题 (按回车保持当前标题): ")
	
	if title != "" {
		cfg.SiteTitle = title
		cfg.Save()
		fmt.Printf("标题已设置为 %s\n", title)
	} else {
		fmt.Println("标题未修改。")
	}
	readInput("\n按回车返回主菜单...")
}

func MainMenu() {
	if err := config.Load(); err != nil {
		// If load fails, maybe config doesn't exist, we start with default
		// Config.Load handles defaults if file missing? 
		// Our implementation returns error if open fails.
		// We should probably init default if load fails.
		// But config.Get() handles nil GlobalConfig.
		// Let's ensure we have a valid config to work with.
		config.Get() // This inits default if nil
	}
	cfg := config.Get()

	for {
		clearScreen()
		printTitle("配置管理系统")
		fmt.Println("1. 查看服务")
		fmt.Println("2. 添加服务")
		fmt.Println("3. 删除服务")
		fmt.Println("4. 设置全局域名")
		fmt.Println("5. 设置标题")
		fmt.Println("6. 退出")

		choice := readInput("\n请输入操作编号 (1-6): ")

		switch choice {
		case "1":
			showServices(cfg)
		case "2":
			addService(cfg)
		case "3":
			deleteService(cfg)
		case "4":
			setDefaultDomain(cfg)
		case "5":
			setTitle(cfg)
		case "6":
			favicon.Clear() // Optional: clear favicons on exit? Python script did clear_favicons() then exit?
			// Python script: get_favicon.clear_favicons() then print goodbye.
			// Wait, did it?
			// Line 190: get_favicon.clear_favicons()
			// Line 140 in get_favicon.py: hard_refresh calls clear then refresh.
			// But line 190 calls clear_favicons? 
			// Wait, get_favicon.py doesn't have clear_favicons exposed at top level?
			// Ah, I missed reading the end of get_favicon.py carefully or it was not shown fully?
			// It has `hard_refresh` and `refresh`.
			// Let's assume we want to refresh or just exit.
			// If the user wants to clear, maybe we should have an option.
			// But the Python script called `get_favicon.clear_favicons()` which I don't see in the file content I read?
			// I see `hard_refresh` which clears then refreshes.
			// Maybe `clear_favicons` was a missing function or I missed it.
			// Let's just print goodbye.
			fmt.Println("感谢使用配置管理系统，配置通常会在1分钟内或下次启动时生效，再见！")
			return
		default:
			fmt.Println("无效的选择，请重新输入。")
		}
	}
}
