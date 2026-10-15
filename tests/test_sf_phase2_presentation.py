import json
import pathlib
import shutil
import subprocess
import unittest

RENDERER = pathlib.Path("wordpress/theme-overrides/inc/sf-explorer-presentation.php")


class Phase2PresentationTests(unittest.TestCase):
    def test_source_safety_contract(self):
        text = RENDERER.read_text(encoding="utf-8")
        self.assertIn("sfex_snapshot()", text)
        self.assertIn("sfex_safe_link(", text)
        self.assertIn("job_summary", text)
        self.assertIn("ukba_sf2_date", text)
        self.assertIn("esc_html(", text)
        self.assertIn("data-search", text)
        self.assertIn("Job description summary", text)
        self.assertNotIn("wp_remote_post(", text)
        self.assertNotIn("file_put_contents(", text)

    @unittest.skipUnless(shutil.which("php"), "PHP not installed")
    def test_php_syntax_and_sample_refresh(self):
        lint = subprocess.run(["php", "-l", str(RENDERER)], capture_output=True, text=True)
        self.assertEqual(lint.returncode, 0, lint.stderr)
        script = r"""<?php
define('ABSPATH', '/tmp');
function add_action($name, $fn, $priority = 10) {}
function add_shortcode($name, $fn) {}
function wp_unique_id() {return 'mock-1';}
function wp_json_encode($v) {return json_encode($v);}
function esc_html($v) {return htmlspecialchars((string)$v, ENT_QUOTES, 'UTF-8');}
function esc_attr($v) {return esc_html($v);}
function esc_url($v) {return esc_html($v);}
function sfex_safe_link($s) {return str_starts_with($s, 'https://www.reed.co.uk/') ? $s : '';}
function sfex_snapshot() {
  return ['refresh'=>['finished_at'=>'2026-10-15T09:00:00Z'], 'vacancies'=>[
    ['title'=>'Salesforce Architect', 'advertiser'=>'Example Plc', 'role_family'=>'Architecture',
     'sector'=>'Technology Services','location'=>'London','employment_type'=>'Permanent',
     'posted_at'=>'2026-10-15T10:25:00Z','specialisms'=>['Commerce Cloud'],
     'url'=>'https://www.reed.co.uk/jobs/test',
     'job_summary'=>['responsibilities'=>'Lead architecture sessions',
       'requirements'=>'Proven Salesforce architecture experience',
       'tools'=>['Commerce Cloud','Order Management'],
       'advert_excerpt'=>null]],
    ['title'=>'Salesforce Analyst', 'advertiser'=>'Other Ltd','posted_at'=>'',
     'specialisms'=>['Sales Cloud'],'url'=>'https://www.reed.co.uk/jobs/second']
  ]];
}
require 'wordpress/theme-overrides/inc/sf-explorer-presentation.php';
$html=ukba_sf2_render_shortcode();
echo json_encode([
  'rows'=>substr_count($html,'class="sfex-row"'),
  'dateUK'=>str_contains($html,'<td>15/10/2026</td>'),
  'timeRemoved'=>!str_contains($html,'<td>2026-10-15T10:25:00Z</td>'),
  'skillsColumnRemoved'=>!str_contains($html,'<th>Skills</th>'),
  'preservesSkillSearch'=>str_contains($html,'commerce cloud'),
  'responsibilities'=>str_contains($html,'Lead architecture sessions'),
  'requirements'=>str_contains($html,'Proven Salesforce architecture experience'),
  'originalUrl'=>str_contains($html,'https://www.reed.co.uk/jobs/test'),
  'unknownDate'=>str_contains($html,'<td>Not specified</td>'),
]);
"""
        run = subprocess.run(["php"], input=script, capture_output=True, text=True, timeout=12)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result["rows"], 2)
        for key, value in result.items():
            if key != "rows":
                self.assertTrue(value, key)


if __name__ == "__main__":
    unittest.main()
