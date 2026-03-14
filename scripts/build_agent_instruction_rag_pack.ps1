param(
    [Parameter(Mandatory = $true)]
    [string]$JsonPath,
    [Parameter(Mandatory = $true)]
    [string]$WorkbookPath
)

$payload = Get-Content -Path $JsonPath -Raw | ConvertFrom-Json
$workbookDir = Split-Path -Parent $WorkbookPath
if (-not (Test-Path $workbookDir)) {
    New-Item -ItemType Directory -Force -Path $workbookDir | Out-Null
}

$excel = $null
$workbook = $null

function Set-HeaderStyle {
    param($Range)
    $Range.Font.Bold = $true
    $Range.Font.Color = 0xFFFFFF
    $Range.Interior.Color = 0x7F6000
}

function Autofit-UsedRange {
    param($Worksheet)
    $Worksheet.UsedRange.Columns.AutoFit() | Out-Null
    $Worksheet.UsedRange.Rows.AutoFit() | Out-Null
}

try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $workbook = $excel.Workbooks.Add()

    $overview = $workbook.Worksheets.Item(1)
    $overview.Name = "Overview"
    $overview.Cells.Item(1, 1).Value2 = "Agent Instruction RAG Pack"
    $overview.Cells.Item(2, 1).Value2 = "Source AGENTS"
    $overview.Cells.Item(2, 2).Value2 = $payload.agents_path
    $overview.Cells.Item(3, 1).Value2 = "Task Count"
    $overview.Cells.Item(3, 2).Value2 = $payload.summary.task_count
    $overview.Cells.Item(4, 1).Value2 = "Repo Count"
    $overview.Cells.Item(4, 2).Value2 = $payload.summary.repo_count
    $overview.Cells.Item(5, 1).Value2 = "High Priority Tasks"
    $overview.Cells.Item(5, 2).Value2 = $payload.summary.high_priority_tasks
    $overview.Cells.Item(7, 1).Value2 = "Workbook purpose"
    $overview.Cells.Item(7, 2).Value2 = "Compact AGENTS instructions into coding-agent task rows, repo lanes, and WinUI host backlog items."
    Set-HeaderStyle $overview.Range("A1:B1")
    $overview.Range("A1:B1").Merge()
    $overview.Range("A1").HorizontalAlignment = -4108

    $taskSheet = $workbook.Worksheets.Add()
    $taskSheet.Name = "RAGTasks"
    $taskHeaders = @(
        "Task ID", "Category", "Agent Role", "Source Section", "Title",
        "Instruction Summary", "Context Chunk", "LoRA Stabilizer", "Embedding Slot",
        "Repo Scope", "Output Artifact", "Priority", "Token Budget", "WinUI Surface",
        "Source Path", "Chunk Weight"
    )
    for ($i = 0; $i -lt $taskHeaders.Count; $i++) {
        $taskSheet.Cells.Item(1, $i + 1).Value2 = $taskHeaders[$i]
    }
    Set-HeaderStyle $taskSheet.Range("A1:P1")

    $row = 2
    foreach ($task in $payload.tasks) {
        $taskSheet.Cells.Item($row, 1).Value2 = $task.task_id
        $taskSheet.Cells.Item($row, 2).Value2 = $task.category
        $taskSheet.Cells.Item($row, 3).Value2 = $task.agent_role
        $taskSheet.Cells.Item($row, 4).Value2 = $task.source_section
        $taskSheet.Cells.Item($row, 5).Value2 = $task.title
        $taskSheet.Cells.Item($row, 6).Value2 = $task.instruction_summary
        $taskSheet.Cells.Item($row, 7).Value2 = $task.context_chunk
        $taskSheet.Cells.Item($row, 8).Value2 = $task.lora_stabilizer
        $taskSheet.Cells.Item($row, 9).Value2 = $task.embedding_slot
        $taskSheet.Cells.Item($row, 10).Value2 = $task.repo_scope
        $taskSheet.Cells.Item($row, 11).Value2 = $task.output_artifact
        $taskSheet.Cells.Item($row, 12).Value2 = $task.priority
        $taskSheet.Cells.Item($row, 13).Value2 = [int]$task.token_budget
        $taskSheet.Cells.Item($row, 14).Value2 = $task.winui_surface
        $taskSheet.Cells.Item($row, 15).Value2 = $task.source_path
        $taskSheet.Cells.Item($row, 16).Formula = "=LEN(F$row)+LEN(G$row)"
        $row++
    }
    $taskSheet.Range("M2:M$row").NumberFormat = "0"

    $repoSheet = $workbook.Worksheets.Add()
    $repoSheet.Name = "RepoInfra"
    $repoHeaders = @("Repo ID", "Repo Name", "Role", "Mutation Policy", "RAG Collection", "Embedding Lane")
    for ($i = 0; $i -lt $repoHeaders.Count; $i++) {
        $repoSheet.Cells.Item(1, $i + 1).Value2 = $repoHeaders[$i]
    }
    Set-HeaderStyle $repoSheet.Range("A1:F1")

    $row = 2
    foreach ($repo in $payload.repos) {
        $repoSheet.Cells.Item($row, 1).Value2 = $repo.repo_id
        $repoSheet.Cells.Item($row, 2).Value2 = $repo.repo_name
        $repoSheet.Cells.Item($row, 3).Value2 = $repo.role
        $repoSheet.Cells.Item($row, 4).Value2 = $repo.mutation_policy
        $repoSheet.Cells.Item($row, 5).Value2 = $repo.rag_collection
        $repoSheet.Cells.Item($row, 6).Value2 = $repo.embedding_lane
        $row++
    }

    $winuiSheet = $workbook.Worksheets.Add()
    $winuiSheet.Name = "WinUIBacklog"
    $winuiHeaders = @("Backlog ID", "Area", "Title", "Implementation Shape", "Purpose", "Source Reference", "Priority")
    for ($i = 0; $i -lt $winuiHeaders.Count; $i++) {
        $winuiSheet.Cells.Item(1, $i + 1).Value2 = $winuiHeaders[$i]
    }
    Set-HeaderStyle $winuiSheet.Range("A1:G1")

    $row = 2
    foreach ($item in $payload.winui_backlog) {
        $winuiSheet.Cells.Item($row, 1).Value2 = $item.backlog_id
        $winuiSheet.Cells.Item($row, 2).Value2 = $item.area
        $winuiSheet.Cells.Item($row, 3).Value2 = $item.title
        $winuiSheet.Cells.Item($row, 4).Value2 = $item.implementation_shape
        $winuiSheet.Cells.Item($row, 5).Value2 = $item.purpose
        $winuiSheet.Cells.Item($row, 6).Value2 = $item.source_reference
        $winuiSheet.Cells.Item($row, 7).Value2 = $item.priority
        $row++
    }

    Autofit-UsedRange $overview
    Autofit-UsedRange $taskSheet
    Autofit-UsedRange $repoSheet
    Autofit-UsedRange $winuiSheet

    $taskSheet.Range("A1:P1").AutoFilter() | Out-Null
    $repoSheet.Range("A1:F1").AutoFilter() | Out-Null
    $winuiSheet.Range("A1:G1").AutoFilter() | Out-Null

    $workbook.SaveAs($WorkbookPath, 51)
    $workbook.Close($true)
    $excel.Quit()
}
finally {
    if ($workbook -ne $null) { [System.Runtime.Interopservices.Marshal]::ReleaseComObject($workbook) | Out-Null }
    if ($excel -ne $null) { [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
