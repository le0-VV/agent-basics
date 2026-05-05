class AgentBasics < Formula
  desc "Baby's first coding agent harness"
  homepage "https://github.com/le0-VV/agent-basics"
  head "https://github.com/le0-VV/agent-basics.git", branch: "main"
  depends_on "rust" => :build
  depends_on "uv"

  def install
    system "cargo", "install", *std_cargo_args
  end

  test do
    require "json"

    project_dir = testpath/"demo-project"
    system bin/"agent-basics", "setup", project_dir

    assert_predicate project_dir/".agents", :exist?
    assert_predicate project_dir/".agents/memory", :exist?
    assert_predicate project_dir/".agents/memory/SCHEMA.md", :exist?
    assert_predicate project_dir/".agents/memory/INDEX.md", :exist?
    assert_predicate project_dir/".agents/memory/memories/preferences/.gitkeep", :exist?
    assert_predicate project_dir/".agents/memory/resources/sources/.gitkeep", :exist?
    assert_predicate project_dir/".agents/openviking/repo.json", :exist?
    refute_predicate project_dir/".agents/memory/rag", :exist?
    assert_predicate project_dir/"Agents.md", :exist?
    assert_predicate project_dir/".agents/AGENT-BASICS.md", :exist?
    assert_predicate project_dir/".gitignore", :exist?
    cd project_dir do
      system bin/"agent-basics", "ov", "record", "preferences", "Formula smoke", "--content", "Dry-run records should not require OpenViking.", "--dry-run"
      IO.popen([(bin/"agent-basics").to_s, "mcp"], "r+") do |pipe|
        pipe.puts(JSON.generate({
          jsonrpc: "2.0",
          id: 1,
          method: "initialize",
          params: {
            protocolVersion: "2025-11-25",
            capabilities: {},
            clientInfo: {
              name: "homebrew-test",
              version: "0",
            },
          },
        }))
        pipe.puts(JSON.generate({ jsonrpc: "2.0", method: "notifications/initialized" }))
        pipe.puts(JSON.generate({ jsonrpc: "2.0", id: 2, method: "tools/list", params: {} }))
        pipe.close_write
        responses = pipe.read.lines.map { |line| JSON.parse(line) }
        assert_equal "agent-basics-openviking", responses.fetch(0).fetch("result").fetch("serverInfo").fetch("name")
        tool_names = responses.fetch(1).fetch("result").fetch("tools").map { |tool| tool.fetch("name") }
        assert_includes tool_names, "search"
        assert_includes tool_names, "record"
      end
    end
    refute_predicate project_dir/".agents/memoryhub", :exist?
    refute_predicate project_dir/".agents/DOCUMENTATIONS.md", :exist?
    refute_predicate project_dir/".agents/MEMORY.md", :exist?
  end
end
