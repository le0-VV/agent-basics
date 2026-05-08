use std::env;
use std::error::Error;
use std::ffi::OsString;
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::{self, Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

const VERSION: &str = env!("CARGO_PKG_VERSION");
const DISPATCHER: &[u8] = include_bytes!("../agent-basics");
const SETUP: &[u8] = include_bytes!("../setup-macos.sh");
const MEMORY_CLI: &[u8] = include_bytes!("../compat/memory-rag/agent-memory.py");
const MEMORY_MCP: &[u8] = include_bytes!("../compat/memory-rag/memory-mcp.py");
const OV_HELPER: &[u8] = include_bytes!("../scripts/agent_basics_ov.py");
const MLX_SERVER: &[u8] = include_bytes!("../scripts/agent_basics_mlx_server.py");
const LICENSE: &[u8] = include_bytes!("../LICENSE");
const THIRD_PARTY_NOTICES: &[u8] = include_bytes!("../THIRD-PARTY-NOTICES.md");

struct Runtime {
    root: PathBuf,
}

const RUNTIME_EXECUTABLES: &[&str] = &[
    "agent-basics",
    "setup-macos.sh",
    "agent-memory.py",
    "memory-mcp.py",
    "agent-basics-ov.py",
    "agent-basics-mlx",
    "agent-basics-mlx-server.py",
];
const RUNTIME_FILES: &[&str] = &["LICENSE", "THIRD-PARTY-NOTICES.md"];

fn main() {
    if let Err(error) = run() {
        eprintln!("agent-basics: {error}");
        process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn Error>> {
    let args: Vec<OsString> = env::args_os().skip(1).collect();
    if args.len() == 1 && args[0] == "--version" {
        println!("agent-basics {VERSION}");
        return Ok(());
    }

    let runtime = ensure_runtime()?;
    let dispatcher = runtime.root.join("agent-basics");
    let mlx_server = sibling_executable("agent-basics-mlx")
        .unwrap_or_else(|| runtime.root.join("agent-basics-mlx"));
    let status = Command::new(&dispatcher)
        .args(args)
        .env(
            "AGENT_BASICS_SETUP_SCRIPT",
            runtime.root.join("setup-macos.sh"),
        )
        .env(
            "AGENT_BASICS_MEMORY_CLI",
            runtime.root.join("agent-memory.py"),
        )
        .env(
            "AGENT_BASICS_MEMORY_MCP",
            runtime.root.join("memory-mcp.py"),
        )
        .env(
            "AGENT_BASICS_OV_HELPER",
            runtime.root.join("agent-basics-ov.py"),
        )
        .env("AGENT_BASICS_MLX_SERVER", mlx_server)
        .env(
            "AGENT_BASICS_MLX_SERVER_SOURCE",
            runtime.root.join("agent-basics-mlx-server.py"),
        )
        .env("AGENT_BASICS_LICENSE", runtime.root.join("LICENSE"))
        .env(
            "AGENT_BASICS_THIRD_PARTY_NOTICES",
            runtime.root.join("THIRD-PARTY-NOTICES.md"),
        )
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .status()?;

    match status.code() {
        Some(code) => process::exit(code),
        None => process::exit(1),
    }
}

fn ensure_runtime() -> Result<Runtime, Box<dyn Error>> {
    let root = runtime_root()?;
    if runtime_complete(&root) {
        return Ok(Runtime { root });
    }

    let marker = root.join(".complete");
    fs::create_dir_all(&root)?;
    write_executable(&root.join("agent-basics"), DISPATCHER)?;
    write_executable(&root.join("setup-macos.sh"), SETUP)?;
    write_executable(&root.join("agent-memory.py"), MEMORY_CLI)?;
    write_executable(&root.join("memory-mcp.py"), MEMORY_MCP)?;
    write_executable(&root.join("agent-basics-ov.py"), OV_HELPER)?;
    write_executable(&root.join("agent-basics-mlx"), MLX_SERVER)?;
    write_executable(&root.join("agent-basics-mlx-server.py"), MLX_SERVER)?;
    fs::write(root.join("LICENSE"), LICENSE)?;
    fs::write(root.join("THIRD-PARTY-NOTICES.md"), THIRD_PARTY_NOTICES)?;
    fs::write(marker, VERSION.as_bytes())?;

    Ok(Runtime { root })
}

fn runtime_complete(root: &Path) -> bool {
    if !root.join(".complete").is_file() {
        return false;
    }
    RUNTIME_EXECUTABLES
        .iter()
        .all(|name| is_executable_file(&root.join(name)))
        && RUNTIME_FILES.iter().all(|name| root.join(name).is_file())
}

fn is_executable_file(path: &Path) -> bool {
    match fs::metadata(path) {
        Ok(metadata) if metadata.is_file() => metadata.permissions().mode() & 0o111 != 0,
        _ => false,
    }
}

fn runtime_root() -> Result<PathBuf, Box<dyn Error>> {
    let executable = env::current_exe()?;
    let metadata = fs::metadata(&executable)?;
    let modified = metadata
        .modified()
        .unwrap_or(SystemTime::UNIX_EPOCH)
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let stamp = format!(
        "agent-basics-runtime-{VERSION}-{}-{modified}",
        metadata.len()
    );
    Ok(env::temp_dir().join(stamp))
}

fn sibling_executable(name: &str) -> Option<PathBuf> {
    let current = env::current_exe().ok()?;
    let candidate = current.parent()?.join(name);
    if candidate.is_file() {
        Some(candidate)
    } else {
        None
    }
}

fn write_executable(path: &Path, content: &[u8]) -> Result<(), Box<dyn Error>> {
    fs::write(path, content)?;
    let mut permissions = fs::metadata(path)?.permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(path, permissions)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn unique_temp_root(name: &str) -> PathBuf {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos();
        env::temp_dir().join(format!(
            "agent-basics-test-{name}-{}-{stamp}",
            process::id()
        ))
    }

    fn write_file(path: &Path, executable: bool) {
        fs::write(path, b"test").unwrap();
        if executable {
            let mut permissions = fs::metadata(path).unwrap().permissions();
            permissions.set_mode(0o755);
            fs::set_permissions(path, permissions).unwrap();
        }
    }

    #[test]
    fn runtime_complete_rejects_marker_without_payload() {
        let root = unique_temp_root("marker-only");
        fs::create_dir_all(&root).unwrap();
        fs::write(root.join(".complete"), VERSION).unwrap();

        assert!(!runtime_complete(&root));

        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn runtime_complete_rejects_non_executable_payload() {
        let root = unique_temp_root("non-executable");
        fs::create_dir_all(&root).unwrap();
        fs::write(root.join(".complete"), VERSION).unwrap();
        for name in RUNTIME_EXECUTABLES {
            write_file(&root.join(name), true);
        }
        for name in RUNTIME_FILES {
            write_file(&root.join(name), false);
        }
        let mut permissions = fs::metadata(root.join("agent-basics"))
            .unwrap()
            .permissions();
        permissions.set_mode(0o644);
        fs::set_permissions(root.join("agent-basics"), permissions).unwrap();

        assert!(!runtime_complete(&root));

        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn runtime_complete_accepts_complete_payload() {
        let root = unique_temp_root("complete");
        fs::create_dir_all(&root).unwrap();
        fs::write(root.join(".complete"), VERSION).unwrap();
        for name in RUNTIME_EXECUTABLES {
            write_file(&root.join(name), true);
        }
        for name in RUNTIME_FILES {
            write_file(&root.join(name), false);
        }

        assert!(runtime_complete(&root));

        fs::remove_dir_all(root).unwrap();
    }
}
