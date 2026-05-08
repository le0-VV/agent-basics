use std::env;
use std::error::Error;
use std::ffi::OsString;
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::os::unix::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{self, Command};
use std::time::{SystemTime, UNIX_EPOCH};

const VERSION: &str = env!("CARGO_PKG_VERSION");
const MLX_SERVER: &[u8] = include_bytes!("../../scripts/agent_basics_mlx_server.py");

struct Runtime {
    server: PathBuf,
}

fn main() {
    if let Err(error) = run() {
        eprintln!("agent-basics-mlx: {error}");
        process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn Error>> {
    let args: Vec<OsString> = env::args_os().skip(1).collect();
    if args.len() == 1 && args[0] == "--version" {
        println!("agent-basics-mlx {VERSION}");
        return Ok(());
    }

    let runtime = ensure_runtime()?;
    let python = mlx_python()?;
    let hf_home = mlx_home()?.join("huggingface");
    let no_proxy = merge_no_proxy(env::var_os("NO_PROXY").or_else(|| env::var_os("no_proxy")));

    let mut command = Command::new(&python);
    command
        .arg0("agent-basics-mlx")
        .arg(runtime.server)
        .args(args)
        .env("HF_HOME", hf_home)
        .env("NO_PROXY", &no_proxy)
        .env("no_proxy", &no_proxy);

    let error = command.exec();
    Err(Box::new(error))
}

fn ensure_runtime() -> Result<Runtime, Box<dyn Error>> {
    let root = runtime_root()?;
    let server = root.join("agent-basics-mlx.py");
    let marker = root.join(".complete");
    if runtime_complete(&root) {
        return Ok(Runtime { server });
    }

    fs::create_dir_all(&root)?;
    write_executable(&server, MLX_SERVER)?;
    fs::write(marker, VERSION.as_bytes())?;
    Ok(Runtime { server })
}

fn runtime_complete(root: &Path) -> bool {
    root.join(".complete").is_file() && is_executable_file(&root.join("agent-basics-mlx.py"))
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
        "agent-basics-mlx-runtime-{VERSION}-{}-{modified}",
        metadata.len()
    );
    Ok(env::temp_dir().join(stamp))
}

fn mlx_home() -> Result<PathBuf, Box<dyn Error>> {
    if let Some(value) = env::var_os("AGENT_BASICS_MLX_HOME") {
        return Ok(PathBuf::from(value));
    }
    let home = env::var_os("HOME").ok_or("HOME is required to locate ~/.agent-basics/mlx")?;
    Ok(PathBuf::from(home).join(".agent-basics").join("mlx"))
}

fn mlx_python() -> Result<PathBuf, Box<dyn Error>> {
    if let Some(value) = env::var_os("AGENT_BASICS_MLX_PYTHON") {
        return Ok(PathBuf::from(value));
    }
    Ok(mlx_home()?.join("venv").join("bin").join("python"))
}

fn merge_no_proxy(value: Option<OsString>) -> String {
    let mut items: Vec<String> = value
        .and_then(|v| v.into_string().ok())
        .unwrap_or_default()
        .split(',')
        .map(str::trim)
        .filter(|item| !item.is_empty())
        .map(ToOwned::to_owned)
        .collect();
    for required in ["localhost", "127.0.0.1", "::1"] {
        if !items.iter().any(|item| item == required) {
            items.push(required.to_string());
        }
    }
    items.join(",")
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
            "agent-basics-mlx-test-{name}-{}-{stamp}",
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
        write_file(&root.join("agent-basics-mlx.py"), false);

        assert!(!runtime_complete(&root));

        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn runtime_complete_accepts_complete_payload() {
        let root = unique_temp_root("complete");
        fs::create_dir_all(&root).unwrap();
        fs::write(root.join(".complete"), VERSION).unwrap();
        write_file(&root.join("agent-basics-mlx.py"), true);

        assert!(runtime_complete(&root));

        fs::remove_dir_all(root).unwrap();
    }
}
