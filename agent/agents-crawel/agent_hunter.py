import os
import sys
import re
import time
import json
import shutil
import subprocess
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlparse
from datetime import datetime
from bs4 import BeautifulSoup

# --- Configuration & Constants ---
CONFIG_FILE = "hunter_config.json"
LOG_FILE = "hunter_execution.log"
TRACKER_FILE = "hunter_tracker.json" # New: Track processed repos

class Logger:
    @staticmethod
    def log(message):
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{ts}] {message}")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")

class ConfigManager:
    @staticmethod
    def load_config():
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {
            "sources": [
                "https://github.com/ashishpatel26/500-AI-Agents-Projects",
                "https://github.com/e2b-dev/awesome-ai-agents",
                "https://github.com/Hannibal046/Awesome-LLM",
                "https://github.com/steven2358/awesome-generative-ai"
            ],
            "keywords": [
                "robotics", "automation", "agent", "autonomous", "slam", "ros",
                "artificial-intelligence", "deep-learning", "reinforcement-learning",
                "computational-physics", "scientific-computing", "simulation"
            ],
            "min_stars": 1000,
            "high_quality_stars": 2000,
            "min_contributors": 100,
            "max_repos_to_process": 20,
            "workspace_dir": "hunter_workspace",
            "use_github_api": True,
            "github_token": "", # Optional: Add token to increase API limits
            "email_config": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "your_email@gmail.com",
                "sender_password": "your_app_password",
                "receiver_email": "your_email@gmail.com"
            }
        }

class RepoTracker:
    """Tracks processing history to avoid redundancy."""
    def __init__(self):
        self.data = {}
        if os.path.exists(TRACKER_FILE):
            try:
                with open(TRACKER_FILE, 'r') as f:
                    self.data = json.load(f)
            except:
                pass

    def save(self):
        with open(TRACKER_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)

    def should_process(self, url):
        if url not in self.data:
            return True

        record = self.data[url]
        # If previously failed build, skip unless it's been a month
        if record.get("status") == "build_failed":
            last_try = datetime.strptime(record.get("last_processed"), "%Y-%m-%d")
            if (datetime.now() - last_try).days < 30:
                return False

        # If success, skip unless forced (logic handled elsewhere)
        if record.get("status") == "success":
            return False

        return True

    def update(self, url, status, details=None):
        self.data[url] = {
            "last_processed": datetime.now().strftime("%Y-%m-%d"),
            "status": status,
            "details": details or {}
        }
        self.save()

class EmailNotifier:
    def __init__(self, config):
        self.config = config.get("email_config", {})
        self.buffer = []

    def add_success(self, repo_data):
        self.buffer.append(repo_data)
        if len(self.buffer) >= 3:
            self.send_notification()
            self.buffer = [] # Reset

    def send_notification(self):
        if not self.config.get("enabled"):
            Logger.log("[Email] Notification disabled.")
            return

        msg = MIMEMultipart()
        msg['From'] = self.config['sender_email']
        msg['To'] = self.config['receiver_email']
        msg['Subject'] = f"[AgentHunter] Found {len(self.buffer)} High-Quality Repos"

        body = "The following high-quality repositories were successfully compiled/run:\n\n"
        for repo in self.buffer:
            body += f"Name: {repo['name']}\n"
            body += f"URL: {repo['url']}\n"
            body += f"Stars: {repo['stars']}\n"
            body += f"Description: {repo['description']}\n"
            body += "-" * 20 + "\n"

        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.starttls()
            server.login(self.config['sender_email'], self.config['sender_password'])
            server.send_message(msg)
            server.quit()
            Logger.log("[Email] Notification sent successfully.")
        except Exception as e:
            Logger.log(f"[Email] Failed to send: {e}")

class NetworkUtils:
    def __init__(self, token=None):
        self.session = requests.Session()

        # Retry strategy
        adapter = requests.adapters.HTTPAdapter(
            max_retries=requests.adapters.Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504]
            )
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        if token:
            headers['Authorization'] = f'token {token}'
        self.session.headers.update(headers)

    def fetch_content(self, url):
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            Logger.log(f"[Net] Requests failed for {url}: {e}")
        return None

    def fetch_json(self, url, params=None):
        try:
            resp = self.session.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            Logger.log(f"[Net] API Request failed: {e}")
        return None

class GitHubSearchCollector:
    def __init__(self, net_utils, config):
        self.net = net_utils
        self.keywords = config.get("keywords", [])
        self.min_stars = config.get("min_stars", 50)
        self.api_url = "https://api.github.com/search/repositories"

    def collect_candidates(self):
        candidates = {}
        Logger.log("[API Collector] Starting GitHub API Search...")

        for kw in self.keywords:
            # Search for C++, Python, C
            for lang in ["python", "c++", "c"]:
                query = f"{kw} language:{lang} stars:>{self.min_stars}"
                params = {"q": query, "sort": "stars", "order": "desc", "per_page": 3}

                data = self.net.fetch_json(self.api_url, params)
                if data and "items" in data:
                    for item in data["items"]:
                        html_url = item.get("html_url")
                        if html_url:
                            candidates[html_url] = f"GitHub API ({kw}/{lang})"
                time.sleep(2)
        return candidates

class SourceCollector:
    def __init__(self, net_utils, config):
        self.net = net_utils
        self.sources = config.get("sources", [])

    def collect_candidates(self):
        candidates = {}
        for source in self.sources:
            content = self.net.fetch_content(source)
            if content:
                matches = re.findall(r'github\.com/([a-zA-Z0-9\-_]+)/([a-zA-Z0-9\-_]+)', content)
                for user, repo in matches:
                    if user.lower() not in ['topics', 'site', 'features', 'about', 'contact', 'pricing', 'sponsors', 'login', 'join']:
                        full_url = f"https://github.com/{user}/{repo}"
                        candidates[full_url] = source
        return candidates

class RepoAnalyzer:
    def __init__(self, net_utils, config):
        self.net = net_utils
        self.config = config
        self.keywords = [k.lower() for k in config.get("keywords", [])]
        self.min_stars = config.get("min_stars", 1000)
        self.hq_stars = config.get("high_quality_stars", 2000)
        self.min_contributors = config.get("min_contributors", 100)

    def get_contributors_count(self, owner, repo):
        # GitHub API usually paginates. Getting > 100 requires checking link headers or page 2
        url = f"https://api.github.com/repos/{owner}/{repo}/contributors?per_page=1&anon=true"
        try:
            resp = self.net.session.get(url)
            if "link" in resp.headers:
                # Parse 'last' page from Link header
                links = resp.headers["link"]
                if 'rel="last"' in links:
                    match = re.search(r'[?&]page=(\d+)[^>]*>; rel="last"', links)
                    if match:
                        return int(match.group(1))
            # Fallback: length of current page (max 100 if per_page=100)
            return 1
        except:
            return 0

    def analyze(self, repo_url):
        time.sleep(1.5) # Rate limit protection
        parts = urlparse(repo_url).path.strip("/").split("/")
        if len(parts) < 2: return None
        owner, repo_name = parts[0], parts[1]

        api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
        api_data = self.net.fetch_json(api_url)

        # Fallback if API fails but we have a URL (likely from an awesome list)
        if not api_data:
            Logger.log(f"    [Analyzer] API failed for {repo_name}, skipping (rate limit or invalid).")
            return {
                "url": repo_url,
                "name": repo_name,
                "stars": 0,
                "description": "Metadata fetch failed (Rate Limit)",
                "topics": [],
                "created_at": "",
                "updated_at": "",
                "contributors": 0,
                "is_high_quality": False,  # API 失败不标记为高质量
                "hq_reasons": ["API Failed - Pending Retry"],
                "score": -1  # 负分，排序到最后
            }

        stars = api_data.get("stargazers_count", 0)
        # Relax constraints: if it's in our list, it's worth checking even if small
        # if stars < self.min_stars: return None

        desc = api_data.get("description") or ""
        topics = api_data.get("topics", [])
        created_at = api_data.get("created_at", "")
        updated_at = api_data.get("updated_at", "")

        # --- High Quality Check ---
        is_high_quality = False
        hq_reasons = []
        contributors = 0

        # 1. Stars check (必须 >= 2000)
        has_high_stars = stars >= self.hq_stars
        if has_high_stars:
            hq_reasons.append(f"Stars: {stars}")

        # 2. Recent Updates (2024/2025/2026)
        try:
            last_update_dt = datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%SZ")
            if last_update_dt.year >= 2024:
                hq_reasons.append(f"Active {last_update_dt.year}")
        except:
            pass

        # 3. Contributors check (必须 >= 100 才算高质量)
        if has_high_stars:
            contributors = self.get_contributors_count(owner, repo_name)
            has_large_community = contributors >= self.min_contributors
            if has_large_community:
                hq_reasons.append(f"Contributors: {contributors}")
                is_high_quality = True  # 同时满足 stars >= 2000 且 contributors >= 100

        # 4. Domain Relevance
        full_text = (str(desc) + " " + " ".join(topics)).lower()
        score = 0
        for kw in self.keywords:
            if kw in full_text: score += 1

        final_score = score * 10 + (stars / 1000.0)
        if is_high_quality: final_score += 50 # Boost HQ repos

        return {
            "url": repo_url,
            "name": repo_name,
            "stars": stars,
            "description": desc,
            "topics": topics,
            "created_at": created_at,
            "updated_at": updated_at,
            "contributors": contributors,
            "is_high_quality": is_high_quality,
            "hq_reasons": hq_reasons,
            "score": final_score
        }

class BuilderRunner:
    def __init__(self, workspace_dir):
        self.workspace_dir = workspace_dir
        self.venv_dir = os.path.join(workspace_dir, "venv")
        self.setup_venv()

    def setup_venv(self):
        if not os.path.exists(self.venv_dir):
            subprocess.run([sys.executable, "-m", "venv", self.venv_dir], check=True)
        self.python_bin = os.path.join(self.venv_dir, "bin", "python")
        self.pip_bin = os.path.join(self.venv_dir, "bin", "pip")

        # Pre-install common scientific/AI libs to increase success rate
        # This helps even if requirements.txt is missing or broken
        Logger.log("[Venv] Pre-installing common libraries...")
        common_libs = ["numpy", "requests", "tqdm"]
        subprocess.run([self.pip_bin, "install"] + common_libs, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def process_repo(self, repo_data):
        repo_name = repo_data['name']
        target_dir = os.path.join(self.workspace_dir, repo_name)

        Logger.log(f"--- Processing {repo_name} ---")

        # Clone
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir) # Clean start for build consistency

        if not self._clone_repo(repo_data['url'], target_dir):
            return False, {"name": repo_name, "url": repo_data['url'], "success": False, "error": "Clone failed"}

        # Detect & Build
        languages = self._detect_languages(target_dir)
        readme_summary = self._extract_readme_summary(target_dir)
        success = False

        if "C++" in languages or "C" in languages:
            if self._build_and_run_cpp(target_dir): success = True

        if "Python" in languages:
            self._install_python_deps(target_dir)
            if self._attempt_run_python(target_dir): success = True

        repo_info = {
            "name": repo_name,
            "url": repo_data['url'],
            "stars": repo_data['stars'],
            "languages": languages,
            "readme_summary": readme_summary,
            "success": success
        }
        return success, repo_info

    def _extract_readme_summary(self, target_dir):
        readme_path = None
        if not os.path.exists(target_dir): return "Directory not found."
        for f in os.listdir(target_dir):
            if f.lower() == "readme.md":
                readme_path = os.path.join(target_dir, f)
                break

        if readme_path:
            try:
                with open(readme_path, 'r', encoding='utf-8') as rf:
                    lines = rf.readlines()
                    summary = []
                    started = False
                    for line in lines:
                        line = line.strip()
                        if not line:
                            if started: break
                            continue
                        if line.startswith(("#", "!", "[", "*", "-", "```")):
                            continue
                        summary.append(line)
                        started = True
                    return " ".join(summary)[:400] + "..." if summary else "No descriptive text found in README."
            except:
                pass
        return "README.md not found."

    def _clone_repo(self, url, target_dir):
        try:
            subprocess.run(["git", "clone", "--depth", "1", url, target_dir],
                           check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            Logger.log("    [Clone] Failed")
            return False

    def _detect_languages(self, target_dir):
        langs = set()
        for root, dirs, files in os.walk(target_dir):
            if ".git" in dirs: dirs.remove(".git")
            for f in files:
                if f.endswith(".py"): langs.add("Python")
                if f.endswith((".cpp", ".cc", ".hpp", "CMakeLists.txt")): langs.add("C++")
                if f.endswith((".c", ".h", "Makefile")): langs.add("C")
        return list(langs)

    def _build_and_run_cpp(self, target_dir):
        build_dir = os.path.join(target_dir, "build")
        os.makedirs(build_dir, exist_ok=True)

        try:
            # 1. CMake
            if os.path.exists(os.path.join(target_dir, "CMakeLists.txt")):
                Logger.log("    [Build C++] Found CMakeLists.txt")
                cmake_cmd = ["cmake", "..", "-DBUILD_EXAMPLES=ON", "-DBUILD_TESTS=ON"]
                subprocess.run(cmake_cmd, cwd=build_dir, check=True, capture_output=True)
                subprocess.run(["make", "-j4"], cwd=build_dir, check=True, capture_output=True)
                self._find_and_run_binary(build_dir) # Look in build dir first
                self._find_and_run_binary(os.path.join(target_dir, "bin")) # Standard bin output
                return True

            # 2. Makefile
            elif os.path.exists(os.path.join(target_dir, "Makefile")):
                Logger.log("    [Build C++] Found Makefile")
                subprocess.run(["make", "-j4"], cwd=target_dir, check=True, capture_output=True)
                self._find_and_run_binary(target_dir)
                return True

            # 3. Simple Compile Fallback
            else:
                for f in os.listdir(target_dir):
                    if f.lower() in ["main.cpp", "main.c", "demo.cpp", "test.cpp"]:
                        Logger.log(f"    [Build C++] Compiling single file: {f}")
                        compiler = "g++" if f.endswith("cpp") else "gcc"
                        subprocess.run([compiler, f, "-o", "a.out"], cwd=target_dir, check=True, capture_output=True)
                        self._run_binary(os.path.join(target_dir, "a.out"))
                        return True
        except Exception as e:
            Logger.log(f"    [Build C++] Failed: {e}")
        return False

    def _find_and_run_binary(self, search_dir):
        if not os.path.exists(search_dir): return
        candidates = []
        for root, _, files in os.walk(search_dir):
            for f in files:
                path = os.path.join(root, f)
                # Filter out standard junk, look for executable bit
                if os.access(path, os.X_OK) and not f.endswith((".sh", ".py", ".o", ".so", ".a", ".cmake")):
                    if "test" in f.lower() or "example" in f.lower() or "demo" in f.lower() or "main" in f.lower() or "benchmark" in f.lower():
                        candidates.append(path)

        # If we found specific targets, run them. If not, pick any executable.
        if candidates:
             # Run up to 2 examples
            for binary in candidates[:2]:
                self._run_binary(binary)
        else:
             # Fallback scan for ANY executable if no "demo/test" found
             for root, _, files in os.walk(search_dir):
                for f in files:
                    path = os.path.join(root, f)
                    if os.access(path, os.X_OK) and not f.endswith((".sh", ".py", ".o", ".so", ".a", ".cmake")):
                        self._run_binary(path)
                        return # Run just one generic one

    def _run_binary(self, binary_path):
        Logger.log(f"    [Run C++] Executing: {os.path.basename(binary_path)}")
        try:
            proc = subprocess.Popen([binary_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                out, _ = proc.communicate(timeout=10) # Increased timeout
                Logger.log(f"        Output: {out.decode('utf-8', errors='ignore')[:500]}...")
            except subprocess.TimeoutExpired:
                proc.kill()
                Logger.log("        Process ran for 10s (Success - Timeout Reached)")
        except Exception as e:
            Logger.log(f"        Execution failed: {e}")

    def _install_python_deps(self, target_dir):
        # 1. Standard requirements.txt
        if os.path.exists(os.path.join(target_dir, "requirements.txt")):
            subprocess.run([self.pip_bin, "install", "-r", "requirements.txt"], cwd=target_dir, capture_output=True)
        # 2. Modern pyproject.toml / setup.py
        elif os.path.exists(os.path.join(target_dir, "setup.py")) or os.path.exists(os.path.join(target_dir, "pyproject.toml")):
            subprocess.run([self.pip_bin, "install", "."], cwd=target_dir, capture_output=True)

    def _attempt_run_python(self, target_dir):
        # Broad search for entry points
        candidates = []
        priority_files = ["main.py", "app.py", "agent.py", "demo.py", "example.py"]

        for root, _, files in os.walk(target_dir):
            if "site-packages" in root or "venv" in root or ".git" in root: continue

            for f in files:
                if not f.endswith(".py"): continue
                path = os.path.join(root, f)

                # Check priority
                if f.lower() in priority_files:
                    candidates.insert(0, path) # Prepend priority
                elif "example" in root.lower() or "demo" in root.lower():
                     candidates.append(path)

        if not candidates:
             # Fallback: Find ANY python file that looks runnable (not __init__)
             for root, _, files in os.walk(target_dir):
                if "site-packages" in root or "venv" in root: continue
                for f in files:
                    if f.endswith(".py") and f != "__init__.py":
                        candidates.append(os.path.join(root, f))

        # Run up to 2 candidates
        run_count = 0
        success = False
        for script in candidates[:2]:
            try:
                Logger.log(f"    [Run Py] Attempting: {os.path.relpath(script, target_dir)}")
                # Run from the root of the repo to ensure imports work if PYTHONPATH isn't set
                env = os.environ.copy()
                env["PYTHONPATH"] = target_dir

                proc = subprocess.Popen([self.python_bin, script], cwd=target_dir, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    out, _ = proc.communicate(timeout=10)
                    Logger.log(f"        Output: {out.decode('utf-8', errors='ignore')[:300]}...")
                    success = True
                    run_count += 1
                except subprocess.TimeoutExpired:
                    proc.kill()
                    Logger.log("        Process ran for 10s (Success)")
                    success = True
                    run_count += 1
            except Exception as e:
                pass

        return success

class AgentHunter:
    def __init__(self):
        self.config = ConfigManager.load_config()
        self.net = NetworkUtils(token=self.config.get("github_token"))
        self.tracker = RepoTracker()
        self.notifier = EmailNotifier(self.config)

        self.page_collector = SourceCollector(self.net, self.config)
        self.api_collector = GitHubSearchCollector(self.net, self.config)
        self.analyzer = RepoAnalyzer(self.net, self.config)

        ws = os.path.abspath(self.config.get("workspace_dir", "hunter_workspace"))
        if not os.path.exists(ws): os.makedirs(ws)
        self.builder = BuilderRunner(ws)
        self.report_data = []

    def run(self):
        Logger.log("=== Agent Hunter Started (Optimized) ===")

        # 1. Collect
        candidates_map = {}
        candidates_map.update(self.page_collector.collect_candidates())
        if self.config.get("use_github_api"):
            candidates_map.update(self.api_collector.collect_candidates())

        # 2. Filter & Analyze
        valid_repos = []
        for url in candidates_map:
            # Check tracker first
            if not self.tracker.should_process(url):
                Logger.log(f"Skipping known repo: {url}")
                continue

            repo_data = self.analyzer.analyze(url)
            if repo_data:
                repo_data['source_origin'] = candidates_map[url]
                valid_repos.append(repo_data)

                # Log High Quality
                if repo_data['is_high_quality']:
                    Logger.log(f"*** HIGH QUALITY FOUND: {repo_data['name']} ***")
                    Logger.log(f"    Reasons: {', '.join(repo_data['hq_reasons'])}")
                    Logger.log(f"    Contributors: {repo_data['contributors']}")

        # 分层筛选策略
        max_to_process = self.config.get("max_repos_to_process", 20)
        hq_stars = self.config.get("high_quality_stars", 2000)
        min_contributors = self.config.get("min_contributors", 100)

        # 第一层：stars >= 2000 且 contributors >= 100 的高质量仓库
        tier1_repos = [
            r for r in valid_repos
            if r['stars'] >= hq_stars and r['contributors'] >= min_contributors
        ]
        tier1_repos.sort(key=lambda x: x['score'], reverse=True)

        Logger.log(f"[Filter] Tier 1 (stars >= {hq_stars}, contributors >= {min_contributors}): {len(tier1_repos)} repos")

        # 如果第一层不足 max_to_process，补充第二层
        targets = tier1_repos[:max_to_process]

        if len(targets) < max_to_process:
            remaining = max_to_process - len(targets)
            # 第二层：stars 在 1000-2000 之间的仓库
            tier2_repos = [
                r for r in valid_repos
                if 1000 <= r['stars'] < hq_stars and r['url'] not in [t['url'] for t in targets]
            ]
            tier2_repos.sort(key=lambda x: x['score'], reverse=True)
            Logger.log(f"[Filter] Tier 2 (1000 <= stars < {hq_stars}): {len(tier2_repos)} repos, adding {min(remaining, len(tier2_repos))}")
            targets.extend(tier2_repos[:remaining])

        # 过滤掉 API 失败的（score < 0）
        targets = [t for t in targets if t['score'] >= 0]

        Logger.log(f"[Filter] Final targets to process: {len(targets)}")

        # 3. Build & Run
        for t in targets:
            build_success, repo_info = self.builder.process_repo(t)
            self.report_data.append(repo_info)

            # Update Tracker
            status = "success" if build_success else "build_failed"
            self.tracker.update(t['url'], status, {"stars": t['stars'], "hq": t['is_high_quality']})

            # Notify if HQ and Success
            if t['is_high_quality'] and build_success:
                Logger.log(f"    [Notify] Adding {t['name']} to notification list.")
                self.notifier.add_success(t)

        # 4. Generate Markdown Summary
        self.generate_report()

        # Final Notification for any remaining buffered successes
        if len(self.notifier.buffer) > 0:
            self.notifier.send_notification()

        Logger.log("=== Agent Hunter Finished ===")

    def generate_report(self):
        report_path = "hunter_readme.md"
        Logger.log(f"[Report] Generating {report_path}...")

        lines = [
            "# Agent Hunter 检索仓库报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            "## 检索仓库概述与编译执行情况\n",
            "| 仓库名称 | 星数 | 状态 | 语言 | 概要说明 |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ]

        for r in self.report_data:
            status = "✅ 成功" if r['success'] else "❌ 失败"
            langs = ", ".join(r.get('languages', []))
            summary = r.get('readme_summary', '').replace('|', '\\|') # Escape pipe
            lines.append(f"| [{r['name']}]({r['url']}) | {r['stars']} | {status} | {langs} | {summary} |")

        # Append to existing or create new? User wants a record, maybe append is better if it runs multiple times?
        # But for now, let's just create/overwrite a fresh one for the session.
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        Logger.log(f"[Report] 报告已保存至 {report_path}")

if __name__ == "__main__":
    agent = AgentHunter()
    agent.run()
