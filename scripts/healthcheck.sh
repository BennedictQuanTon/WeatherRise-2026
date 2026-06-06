echo ""
echo "=== GPU Status ==="
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader,nounits | while IFS=, read idx name used total; do
  pct=$((used * 100 / total))
  echo "  GPU $idx: $name | ${used}MB / ${total}MB (${pct}%)"
done
echo "=== Done ==="