# Offline source adapter only. Never evaluate object tags or upstream code; bound data-only anchor expansion.
require 'psych'
require 'json'
abort 'parser_version' unless RUBY_VERSION == '4.0.7' && Psych::VERSION == '5.3.1' && JSON::VERSION == '2.18.0'
raw = File.binread(ARGV.fetch(0))
abort 'source_too_large' if raw.bytesize > 64 * 1024 * 1024
ast = Psych.parse_stream(raw)
abort 'yaml_document_count' unless ast.children.length == 1
@visited = 0
def check(node, depth = 0)
  @visited += 1
  abort 'yaml_ast_bounds' if depth > 64 || @visited > 2_000_000
  if node.is_a?(Psych::Nodes::Mapping)
    keys = node.children.each_slice(2).map { |key, _| key.value if key.is_a?(Psych::Nodes::Scalar) }
    abort 'duplicate_or_complex_yaml_key' if keys.include?(nil) || keys.uniq.length != keys.length
  end
  node.children&.each { |child| check(child, depth + 1) }
end
check(ast)
value = Psych.safe_load(raw, permitted_classes: [], permitted_symbols: [], aliases: true)
@expanded = 0
def ordered(value, depth = 0)
  @expanded += 1
  abort 'yaml_expansion_bounds' if depth > 64 || @expanded > 2_000_000
  case value
  when Hash
    abort 'unsupported_yaml_key' unless value.keys.all? { |key| key.is_a?(String) || key.is_a?(Integer) }
    pairs = value.map { |key, child| [key.to_s, child] }
    abort 'duplicate_normalized_yaml_key' unless pairs.map(&:first).uniq.length == pairs.length
    pairs.sort_by(&:first).to_h { |key, child| [key, ordered(child, depth + 1)] }
  when Array then value.map { |child| ordered(child, depth + 1) }
  else value
  end
end
STDOUT.write(JSON.generate(ordered(value)))
