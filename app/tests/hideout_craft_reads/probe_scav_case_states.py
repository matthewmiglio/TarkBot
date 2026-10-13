"""Read the open Scav Case panel once and dump what the bot sees: both roll anchors and their state.

App layer: craft.find / read_craft over SCAV_CASE (moonshine) and SCAV_CASE_INTEL (intelligence),
plus the roll-agnostic reads the collect pass uses (lit_get_items) and every START / GET ITEMS /
timer match with its button brightness.

Read-only by default: no clicks, no wheel. It looks at the list where it sits, so a roll below the
fold reads as absent here. --scroll first makes the pass's own entry scroll
(craft.scroll_scav_case_list: one dead-space click and one wheel), which starts nothing. Writes the frame and a json of every match to
tests/output/scav_case_states/, which is what the annotated picture is drawn from.

**Game**: Tarkov up with the Scav Case panel open.
Run:  python tests/hideout_craft_reads/probe_scav_case_states.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import craft_bot  # noqa: E402
import screen  # noqa: E402
from gui import settings  # noqa: E402
from interact import craft, find  # noqa: E402

out_dir = Path(__file__).resolve().parents[1] / 'output' / 'scav_case_states'
out_dir.mkdir(parents=True, exist_ok=True)

region = craft_bot.build(settings.load(), None).region
if '--scroll' in sys.argv:  # the one wheel the scav case pass makes on entry: a click and a scroll, nothing else
    craft.scroll_scav_case_list(region)
shot = screen.grab(region).convert('RGB')
shot.save(out_dir / 'frame.png')


def box(b, **extra):
    return dict(x=b.left - region[0], y=b.top - region[1], w=b.width, h=b.height, **extra)


report = {'region': list(region), 'scale': find.scale(),
          'panel_open': bool(find.find(craft.SCAV_CASE_ACTIVE_TARGET, region)), 'rolls': {},
          'start': [box(b, brightness=craft.button_brightness(b), ready=craft.is_ready(b))
                    for b in find.find_all(craft.START_TARGET, region)],
          'get_items': [box(b, brightness=craft.button_brightness(b), lit=craft.get_items_highlighted(b))
                        for b in find.find_all(craft.GET_ITEMS_TARGET, region)],
          'timers': [box(b) for b in find.find_all(craft.TIMER_TARGET, region)],
          'lit_get_items': [box(b) for b in craft.lit_get_items(region)]}

for c in (craft.SCAV_CASE, craft.SCAV_CASE_INTEL):
    anchors = find.find_all(c.output_target, region)
    entry = {'target': c.output_target, 'anchors': [box(b) for b in anchors]}
    try:
        r = craft.read_craft(c, region)
        entry.update(state=r.state, output=box(r.output),
                     band=dict(zip('xywh', (r.band[0] - region[0], r.band[1] - region[1], *r.band[2:]))),
                     start=box(r.start) if r.start else None,
                     get_items=box(r.get_items) if r.get_items else None,
                     inputs=[(n, ok) for n, ok, _ in (r.inputs or [])])
    except (LookupError, craft.Blind) as e:
        entry.update(state=None, error=str(e))
    report['rolls'][c.name] = entry
    print(f'{c.name:>16}: {entry.get("state")}  anchors={len(anchors)}  {entry.get("error", "")}')

(out_dir / 'report.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
