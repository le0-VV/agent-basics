class AgentBasics < Formula
  desc "1 command to setup a directory for reliable agent operations"
  homepage "https://github.com/le0-VV/agent-basics"
  head "https://github.com/le0-VV/agent-basics.git", branch: "main"
  depends_on "uv"

  def install
    libexec.install "setup-macos.sh"
    libexec.install ".agents/memory/rag/agent-memory.py"
    libexec.install ".agents/memory/rag/memory-mcp.py"

    (bin/"agent-basics").write <<~EOS
      #!/usr/bin/env bash
      exec "#{libexec}/setup-macos.sh" "$@"
    EOS
    (bin/"agent-basics-memory").write <<~EOS
      #!/usr/bin/env bash
      exec "#{libexec}/agent-memory.py" "$@"
    EOS
    (bin/"agent-basics-memory-mcp").write <<~EOS
      #!/usr/bin/env bash
      exec "#{libexec}/memory-mcp.py" "$@"
    EOS
    chmod 0755, bin/"agent-basics"
    chmod 0755, bin/"agent-basics-memory"
    chmod 0755, bin/"agent-basics-memory-mcp"
  end

  test do
    require "json"
    require "socket"

    project_dir = testpath/"demo-project"
    server = TCPServer.new("127.0.0.1", 0)
    port = server.addr[1]
    pid = fork do
      loop do
        socket = server.accept
        request_line = socket.gets
        headers = {}

        while (line = socket.gets)
          break if line == "\r\n"

          key, value = line.split(":", 2)
          headers[key.downcase] = value.strip if key && value
        end

        content_length = headers.fetch("content-length", "0").to_i
        request_body = content_length.positive? ? socket.read(content_length) : ""

        if request_line&.include?("POST /v1/embeddings")
          payload = JSON.parse(request_body)
          inputs = payload.fetch("input")
          inputs = [inputs] if inputs.is_a?(String)
          body = JSON.generate({
            object: "list",
            data: inputs.each_with_index.map do |_input, index|
              {
                object: "embedding",
                embedding: Array.new(64) { |dimension| dimension.to_f / 100.0 },
                index: index,
              }
            end,
            model: "test-embedding",
            usage: {
              prompt_tokens: 0,
              total_tokens: 0,
            },
          })
          status = "200 OK"
        else
          body = JSON.generate({ error: "not found" })
          status = "404 Not Found"
        end

        socket.write "HTTP/1.1 #{status}\r\n"
        socket.write "Content-Type: application/json\r\n"
        socket.write "Content-Length: #{body.bytesize}\r\n"
        socket.write "Connection: close\r\n\r\n"
        socket.write body
        socket.close
      end
    end
    server.close

    begin
      system(
        {
          "AGENT_BASICS_EMBEDDING_BASE_URL" => "http://127.0.0.1:#{port}/v1",
          "AGENT_BASICS_EMBEDDING_MODEL" => "test-embedding",
          "AGENT_BASICS_EMBEDDING_API_KEY" => "",
        },
        bin/"agent-basics",
        project_dir,
      )
    ensure
      Process.kill("TERM", pid)
      Process.wait(pid)
    end

    assert_predicate project_dir/".agents", :exist?
    assert_predicate project_dir/".agents/memory", :exist?
    assert_predicate project_dir/".agents/memory/SCHEMA.md", :exist?
    assert_predicate project_dir/".agents/memory/INDEX.md", :exist?
    assert_predicate project_dir/".agents/memory/rag/config.json", :exist?
    assert_predicate project_dir/".agents/memory/rag/agent-memory.py", :exist?
    assert_predicate project_dir/".agents/memory/rag/memory-mcp.py", :exist?
    assert_predicate project_dir/".agents/memory/rag/index.sqlite", :exist?
    assert_predicate project_dir/".git/hooks/pre-commit", :exist?
    assert_predicate project_dir/"Agents.md", :exist?
    assert_predicate project_dir/".agents/AGENT-BASICS.md", :exist?
    assert_predicate project_dir/".gitignore", :exist?
    cd project_dir do
      system bin/"agent-basics-memory", "validate"
      IO.popen((bin/"agent-basics-memory-mcp").to_s, "r+") do |pipe|
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
        assert_equal "agent-basics-memory", responses.fetch(0).fetch("result").fetch("serverInfo").fetch("name")
        tool_names = responses.fetch(1).fetch("result").fetch("tools").map { |tool| tool.fetch("name") }
        assert_includes tool_names, "memory_search"
        assert_includes tool_names, "memory_record"
      end
    end
    refute_predicate project_dir/".agents/memoryhub", :exist?
    refute_predicate project_dir/".agents/DOCUMENTATIONS.md", :exist?
    refute_predicate project_dir/".agents/MEMORY.md", :exist?
  end
end
