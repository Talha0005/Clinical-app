from services.agent_response_formatter import AgentResponseFormatter

sample = {
    'definition': 'A fever is a body temperature above normal.',
    'aetiology': 'Usually due to infections',
    'symptoms': ['Headache', 'Muscle aches', 'Fatigue'],
    'management': 'Rest, fluids, antipyretics',
    # Minimal fields to trigger fallbacks for the rest
}

fmt = AgentResponseFormatter()
res = fmt.format_agent_response_for_admin(sample, condition_name='Fever')
std = res['standardized_format']
print('Total categories:', len(std))
for i, (k, v) in enumerate(std.items(), 1):
    if isinstance(v, list):
        vshow = v if len(v) <= 3 else v[:3] + ['...']
    else:
        vshow = v
    print(f"{i:02d}. {k}: {vshow}")
