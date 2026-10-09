$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$wordApp = New-Object -ComObject Word.Application
$wordApp.Visible = $false
$wordApp.DisplayAlerts = 0
try {
    $reportDoc = $wordApp.Documents.Open((Join-Path $projectRoot 'tmp\Part_2_Report.rtf'), $false, $false)
    $reportDoc.Paragraphs.Item(1).Style = 'Title'
    $reportDoc.SaveAs2([string](Join-Path $projectRoot 'submission\Part_2_Report.docx'), 12)
    $reportDoc.ExportAsFixedFormat([string](Join-Path $projectRoot 'tmp\Part_2_Report.pdf'), 17)
    Write-Output "Rendered pages: $($reportDoc.ComputeStatistics(2))"
    $reportDoc.Close(0)
} finally {
    $wordApp.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wordApp) | Out-Null
}
