class AgentBasics < Formula
  desc "1 command to setup a directory for reliable agent operations"
  homepage "https://github.com/le0-VV/agent-basics"
  head "https://github.com/le0-VV/agent-basics.git", branch: "main"
  depends_on "uv"

  def install
    libexec.install "setup-macos.sh"

    (bin/"agent-basics").write <<~EOS
      #!/usr/bin/env bash
      exec "#{libexec}/setup-macos.sh" "$@"
    EOS
  end

  test do
    project_dir = testpath/"demo-project"
    memoryhub_config_dir = testpath/".memoryhub"
    memoryhub_bin = memoryhub_config_dir/"venv/bin"
    memoryhub_bin.mkpath
    (memoryhub_bin/"memoryhub").write <<~EOS
      #!/usr/bin/env bash
      set -euo pipefail
      case "$*" in
        doctor)
          exit 0
          ;;
        "project list --json")
          printf '{"projects":[]}'
          ;;
        project\\ add*)
          exit 0
          ;;
        *)
          echo "unexpected memoryhub command: $*" >&2
          exit 1
          ;;
      esac
    EOS
    chmod 0755, memoryhub_bin/"memoryhub"

    system({ "MEMORYHUB_CONFIG_DIR" => memoryhub_config_dir.to_s }, bin/"agent-basics", project_dir)

    assert_predicate project_dir/".agents", :exist?
    assert_predicate project_dir/".agents/memoryhub", :exist?
    assert_predicate project_dir/"Agents.md", :exist?
    assert_predicate project_dir/".agents/INSTRUCTIONS.md", :exist?
    assert_predicate project_dir/".gitignore", :exist?
    assert_predicate memoryhub_config_dir/"projects/demo-project", :symlink?
    refute_predicate project_dir/".agents/DOCUMENTATIONS.md", :exist?
    refute_predicate project_dir/".agents/MEMORY.md", :exist?
  end
end
