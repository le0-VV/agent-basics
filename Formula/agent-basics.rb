class AgentBasics < Formula
  desc "1 command to setup a directory for reliable agent operations"
  homepage "https://github.com/le0-VV/agent-basics"
  head "https://github.com/le0-VV/agent-basics.git", branch: "main"
  depends_on "llama.cpp"

  def install
    libexec.install ".agents/openviking/models"
    libexec.install "setup-macos.sh"

    (bin/"agent-basics").write <<~EOS
      #!/usr/bin/env bash
      export AGENT_BASICS_MODEL_DIR="#{libexec}/models"
      exec "#{libexec}/setup-macos.sh" "$@"
    EOS
  end

  test do
    project_dir = testpath/"demo-project"
    ov_bin = project_dir/".agents/openviking/venv/bin"
    ov_bin.mkpath
    (ov_bin/"openviking-server").write <<~EOS
      #!/usr/bin/env bash
      set -euo pipefail
      case "$1" in
        doctor)
          exit 0
          ;;
        *)
          exit 1
          ;;
      esac
    EOS
    (ov_bin/"python").write <<~EOS
      #!/usr/bin/env bash
      set -euo pipefail
      exec /usr/bin/python3 "$@"
    EOS
    chmod 0755, ov_bin/"openviking-server"
    chmod 0755, ov_bin/"python"

    (project_dir/".agents/openviking").mkpath
    (project_dir/".agents/openviking/ov.conf").write "\n"
    (project_dir/".agents/openviking/ovcli.conf").write "\n"

    system bin/"agent-basics", project_dir

    assert_predicate project_dir/".agents", :exist?
    assert_predicate project_dir/".agents/openviking", :exist?
    assert_predicate project_dir/"Agents.md", :exist?
    assert_predicate project_dir/".agents/INSTRUCTIONS.md", :exist?
    assert_predicate project_dir/".gitignore", :exist?
    refute_predicate project_dir/".agents/DOCUMENTATIONS.md", :exist?
    refute_predicate project_dir/".agents/MEMORY.md", :exist?
  end
end
