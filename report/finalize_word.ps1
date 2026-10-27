# finalize_word.ps1 -- open report/out/Project_Report.docx in Microsoft Word, update the table
# of contents, the lists of figures and tables and the page numbers, save it, and export
# report/out/Project_Report.pdf. Changes no text.
# Run: powershell -ExecutionPolicy Bypass -File report/finalize_word.ps1
$out = Join-Path $PSScriptRoot "out"
$docx = Join-Path $out "Project_Report.docx"
$pdf = Join-Path $out "Project_Report.pdf"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($docx, $false, $false, $false)
    $doc.Fields.Update() | Out-Null
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() | Out-Null }
    $doc.Repaginate()
    foreach ($toc in $doc.TablesOfContents) { $toc.UpdatePageNumbers() | Out-Null }
    $doc.Save()
    $doc.ExportAsFixedFormat($pdf, 17)
    "pages: " + $doc.ComputeStatistics(2)
    "words: " + $doc.ComputeStatistics(0)
    $doc.Close()
} finally {
    $word.Quit()
}
