class AgentBasics < Formula
  desc "1 command to setup a directory for reliable agent operations"
  homepage "https://github.com/le0-VV/agent-basics"
  head "https://github.com/le0-VV/agent-basics.git", branch: "main"

  def install
    bin.install "setup-macos.sh" => "agent-basics"
  end

  test do
    project_dir = testpath/"demo-project"
    system bin/"agent-basics", project_dir

    assert_predicate project_dir/".agents", :exist?
    assert_predicate project_dir/"Agents.md", :exist?
    assert_predicate project_dir/".agents/INSTRUCTIONS.md", :exist?
    assert_predicate project_dir/".gitignore", :exist?
  end
end
