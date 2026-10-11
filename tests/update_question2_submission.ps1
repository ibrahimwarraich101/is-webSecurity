$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$name = '23F-0590-0669_BSCS-7A_IS-A2'
$package = Join-Path $projectRoot "submission\$name"
$question2 = Join-Path $package 'Question_2'
foreach ($file in @('app.py', 'README.md', 'run.ps1', 'seed-data.sql')) {
    Copy-Item -LiteralPath (Join-Path $projectRoot $file) -Destination $question2 -Force
}
foreach ($folder in @('static', 'tests')) {
    Copy-Item -LiteralPath (Join-Path $projectRoot $folder) -Destination $question2 -Recurse -Force
}
Copy-Item -LiteralPath (Join-Path $projectRoot 'submission\screenshots') -Destination (Join-Path $question2 'submission') -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'submission\verification.json'), (Join-Path $projectRoot 'submission\Part_2_Report.docx') -Destination (Join-Path $question2 'submission') -Force

python (Join-Path $projectRoot 'tests\merge_question2_report.py')
if ($LASTEXITCODE -ne 0) { throw 'Combined report update failed' }

$readme = Join-Path $package 'README.txt'
$text = Get-Content -LiteralPath $readme -Raw
$text = $text.Replace('37 browser captures', '41 browser captures verified on 11 October 2026')
$text = $text.Replace('Obtain full-screen timestamped captures if the instructor requires the whole desktop.', 'Part 1 explicitly requires full-screen system-date/time captures. Part 2 includes matched browser evidence for attacks and defenses.')
$text = $text.Replace('Live GitHub publication and commit-history compliance were not verified during packaging.', 'GitHub main matched the existing three development commits before this Question 2 update. See the project branch for updated source and evidence.')
Set-Content -LiteralPath $readme -Value $text -Encoding UTF8
Compress-Archive -LiteralPath $package -DestinationPath (Join-Path $projectRoot "submission\$name.zip") -Force
Compress-Archive -LiteralPath $question2 -DestinationPath (Join-Path $projectRoot 'submission\Part2_CampusHub.zip') -Force
Write-Output 'Updated Question 2 package and both ZIP archives.'
