class AgentBasics < Formula
  desc "Baby's first coding agent harness"
  homepage "https://github.com/le0-VV/agent-basics"
  license "MIT"
  head "https://github.com/le0-VV/agent-basics.git", branch: "main"
  depends_on "rust" => :build
  depends_on "uv"

  def install
    system "cargo", "install", *std_cargo_args
  end

  def post_install
    system bin/"agent-basics", "ov", "bootstrap-system",
           "--service", "never",
           "--runtime", "mlx",
           "--runtime-best-effort"
  end

  def caveats
    <<~EOS
      agent-basics bootstraps OpenViking during install and configures the
      agent-basics MLX runtime as the default local OpenAI-compatible runtime.
      Repo setup verifies or starts the global OpenViking service and creates
      repo-local source-store metadata.
      To repair or rerun that step manually:
        agent-basics ov bootstrap-system
        agent-basics mlx bootstrap
    EOS
  end

  test do
    require "json"

    system bin/"agent-basics-mlx", "--version"

    project_dir = testpath/"demo-project"
    with_env("AGENT_BASICS_TEST_SKIP_OPENVIKING_CHECK" => "1") do
      system bin/"agent-basics", "setup", project_dir
    end

    assert_path_exists project_dir/".agents"
    assert_path_exists project_dir/".agents/memory"
    assert_path_exists project_dir/".agents/memory/SCHEMA.md"
    assert_path_exists project_dir/".agents/memory/INDEX.md"
    assert_path_exists project_dir/".agents/memory/memories/preferences/.gitkeep"
    assert_path_exists project_dir/".agents/memory/resources/sources/.gitkeep"
    assert_path_exists project_dir/".agents/openviking/repo.json"
    refute_path_exists project_dir/".agents/memory/rag"
    assert_path_exists project_dir/"Agents.md"
    assert_path_exists project_dir/".agents/AGENT-BASICS.md"
    assert_path_exists project_dir/".gitignore"
    cd project_dir do
      system bin/"agent-basics", "ov", "record", "preferences", "Formula smoke",
             "--content", "Dry-run records should not require OpenViking.",
             "--dry-run"
      IO.popen([(bin/"agent-basics").to_s, "mcp"], "r+") do |pipe|
        initialize_request = {
          jsonrpc: "2.0",
          id:      1,
          method:  "initialize",
          params:  {
            protocolVersion: "2025-11-25",
            capabilities:    {},
            clientInfo:      {
              name:    "homebrew-test",
              version: "0",
            },
          },
        }
        pipe.puts JSON.generate(initialize_request)
        pipe.puts JSON.generate(jsonrpc: "2.0", method: "notifications/initialized")
        pipe.puts JSON.generate(jsonrpc: "2.0", id: 2, method: "tools/list", params: {})
        pipe.close_write
        responses = pipe.read.lines.map { |line| JSON.parse(line) }
        assert_equal "agent-basics-openviking", responses.fetch(0).fetch("result").fetch("serverInfo").fetch("name")
        tool_names = responses.fetch(1).fetch("result").fetch("tools").map { |tool| tool.fetch("name") }
        assert_includes tool_names, "search"
        assert_includes tool_names, "record"
      end
    end
    refute_path_exists project_dir/".agents/memoryhub"
    refute_path_exists project_dir/".agents/DOCUMENTATIONS.md"
    refute_path_exists project_dir/".agents/MEMORY.md"
  end
end
