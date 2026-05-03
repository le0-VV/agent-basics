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
const MEMORY_CLI: &[u8] = include_bytes!("../.agents/memory/rag/agent-memory.py");
const MEMORY_MCP: &[u8] = include_bytes!("../.agents/memory/rag/memory-mcp.py");

struct Runtime {
    root: PathBuf,
}

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
    let marker = root.join(".complete");
    if marker.is_file() {
        return Ok(Runtime { root });
    }

    fs::create_dir_all(&root)?;
    write_executable(&root.join("agent-basics"), DISPATCHER)?;
    write_executable(&root.join("setup-macos.sh"), SETUP)?;
    write_executable(&root.join("agent-memory.py"), MEMORY_CLI)?;
    write_executable(&root.join("memory-mcp.py"), MEMORY_MCP)?;
    fs::write(marker, VERSION.as_bytes())?;

    Ok(Runtime { root })
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

fn write_executable(path: &Path, content: &[u8]) -> Result<(), Box<dyn Error>> {
    fs::write(path, content)?;
    let mut permissions = fs::metadata(path)?.permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(path, permissions)?;
    Ok(())
}
