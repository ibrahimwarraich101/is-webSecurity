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

$wordApp = New-Object -ComObject Word.Application
$wordApp.Visible = $false
$wordApp.DisplayAlerts = 0
try {
    $workingCopy = Join-Path $projectRoot 'tmp\Combined_Question2_Update.docx'
    Copy-Item -LiteralPath (Join-Path $projectRoot "submission\$name.docx") -Destination $workingCopy -Force
    $doc = $wordApp.Documents.Open($workingCopy, $false, $false)
    $start = $doc.Content.Duplicate
    if (-not $start.Find.Execute('Question 2 CampusHub Web Security Project')) { throw 'Question 2 boundary missing' }
    $finish = $doc.Range($start.End, $doc.Content.End)
    if (-not $finish.Find.Execute('Submission Evidence Review')) { throw 'Review boundary missing' }
    $replace = $doc.Range($start.Start, $finish.Start)
    $replace.Delete() | Out-Null
    $replace.Collapse(1)
    Write-Output "Replacing Question 2 report section"
    $replace.InsertFile((Join-Path $projectRoot 'submission\Part_2_Report.docx'))
    $review = $doc.Content.Duplicate
    if ($review.Find.Execute('Question 2 includes both modes,')) {
        $review.Paragraphs.Item(1).Range.Text = "Question 2 includes both versions, frontend and backend source, seed data, exact attack payloads, defenses and 41 fresh browser captures dated 11 October 2026. Six HTTP regression test methods and the Chromium checks passed. The reliable external CSRF demonstration uses localhost:8001 and verifies server-side rejection in safe mode.`r"
    }
    $review = $doc.Content.Duplicate
    if ($review.Find.Execute('The checklist requires full-screen timestamped screenshots.')) {
        $review.Paragraphs.Item(1).Range.Text = "Part 1 explicitly requires full-screen screenshots with visible system date and time. Part 2 requires matching exploit and safe-version evidence; its browser captures include an application date and time. Part 1 evidence requirements remain separate from this Question 2 update.`r"
    }
    $doc.SaveAs2((Join-Path $projectRoot "submission\$name.docx"), 12)
    $doc.ExportAsFixedFormat((Join-Path $projectRoot 'tmp\Combined_Report.pdf'), 17)
    Write-Output "Combined report pages: $($doc.ComputeStatistics(2)); images: $($doc.InlineShapes.Count)"
    $doc.Close(0)
} finally {
    if ($doc) { try { $doc.Close(0) } catch {} }
    $wordApp.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wordApp) | Out-Null
}

$readme = Join-Path $package 'README.txt'
$text = Get-Content -LiteralPath $readme -Raw
$text = $text.Replace('37 browser captures', '41 browser captures verified on 11 October 2026')
$text = $text.Replace('Obtain full-screen timestamped captures if the instructor requires the whole desktop.', 'Part 1 explicitly requires full-screen system-date/time captures. Part 2 includes matched browser evidence for attacks and defenses.')
$text = $text.Replace('Live GitHub publication and commit-history compliance were not verified during packaging.', 'GitHub main matched the existing three development commits before this Question 2 update. See the project branch for updated source and evidence.')
Set-Content -LiteralPath $readme -Value $text -Encoding UTF8
Compress-Archive -LiteralPath $package -DestinationPath (Join-Path $projectRoot "submission\$name.zip") -Force
Compress-Archive -LiteralPath $question2 -DestinationPath (Join-Path $projectRoot 'submission\Part2_CampusHub.zip') -Force
Write-Output 'Updated Question 2 package and both ZIP archives.'
