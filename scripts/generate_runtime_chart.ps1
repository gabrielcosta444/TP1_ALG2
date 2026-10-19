param(
    [string]$OutputPath = "docs/images/grafico_tempo_busca.png"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$width = 1800
$height = 1100
$left = 175
$right = 90
$top = 245
$bottom = 170
$plotWidth = $width - $left - $right
$plotHeight = $height - $top - $bottom
$yMaximum = 20.0
$subtitleText = (
    "Medi$([char]0xE7)$([char]0xF5)es pontuais do servi$([char]0xE7)o " +
    "de consulta; menor tempo $([char]0xE9) melhor"
)
$xAxisText = "Tamanho da frota (n$([char]0xFA)mero de entregadores)"
$sourceText = (
    "Fonte: elabora$([char]0xE7)$([char]0xE3)o pr$([char]0xF3)pria com " +
    "base nas execu$([char]0xE7)$([char]0xF5)es do script benchmark_queries.py."
)

$series = @(
    @{
        Label = "Raio 0,5 km"
        Color = [System.Drawing.Color]::FromArgb(22, 58, 95)
        Marker = "circle"
        Dash = [System.Drawing.Drawing2D.DashStyle]::Solid
        Values = @(0.4494, 0.5051, 2.1705)
    },
    @{
        Label = "Raio 1 km"
        Color = [System.Drawing.Color]::FromArgb(185, 139, 0)
        Marker = "square"
        Dash = [System.Drawing.Drawing2D.DashStyle]::Dash
        Values = @(0.2517, 0.6146, 7.3679)
    },
    @{
        Label = "Raio 2 km"
        Color = [System.Drawing.Color]::FromArgb(213, 94, 0)
        Marker = "triangle"
        Dash = [System.Drawing.Drawing2D.DashStyle]::DashDot
        Values = @(0.2150, 0.6044, 9.6615)
    },
    @{
        Label = "Raio 5 km"
        Color = [System.Drawing.Color]::FromArgb(162, 59, 114)
        Marker = "diamond"
        Dash = [System.Drawing.Drawing2D.DashStyle]::Dot
        Values = @(0.2654, 1.3779, 17.1838)
    }
)

$fleetLabels = @("100", "1.000", "10.000")
$xCoordinates = @(
    [single]($left + 90),
    [single]($left + $plotWidth / 2),
    [single]($left + $plotWidth - 90)
)

function Get-YCoordinate([double]$value) {
    return [single]($top + $plotHeight - ($value / $yMaximum) * $plotHeight)
}

function Draw-Marker(
    [System.Drawing.Graphics]$Graphics,
    [System.Drawing.Color]$Color,
    [string]$Shape,
    [single]$X,
    [single]$Y
) {
    $size = 15
    $brush = New-Object System.Drawing.SolidBrush($Color)
    $whitePen = New-Object System.Drawing.Pen([System.Drawing.Color]::White, 3)
    try {
        switch ($Shape) {
            "circle" {
                $Graphics.FillEllipse($brush, $X - $size, $Y - $size, 2 * $size, 2 * $size)
                $Graphics.DrawEllipse($whitePen, $X - $size, $Y - $size, 2 * $size, 2 * $size)
            }
            "square" {
                $Graphics.FillRectangle($brush, $X - $size, $Y - $size, 2 * $size, 2 * $size)
                $Graphics.DrawRectangle($whitePen, $X - $size, $Y - $size, 2 * $size, 2 * $size)
            }
            "triangle" {
                $points = [System.Drawing.PointF[]]@(
                    [System.Drawing.PointF]::new($X, $Y - $size - 2),
                    [System.Drawing.PointF]::new($X - $size - 2, $Y + $size),
                    [System.Drawing.PointF]::new($X + $size + 2, $Y + $size)
                )
                $Graphics.FillPolygon($brush, $points)
                $Graphics.DrawPolygon($whitePen, $points)
            }
            "diamond" {
                $points = [System.Drawing.PointF[]]@(
                    [System.Drawing.PointF]::new($X, $Y - $size - 2),
                    [System.Drawing.PointF]::new($X - $size - 2, $Y),
                    [System.Drawing.PointF]::new($X, $Y + $size + 2),
                    [System.Drawing.PointF]::new($X + $size + 2, $Y)
                )
                $Graphics.FillPolygon($brush, $points)
                $Graphics.DrawPolygon($whitePen, $points)
            }
        }
    }
    finally {
        $brush.Dispose()
        $whitePen.Dispose()
    }
}

$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$graphics.Clear([System.Drawing.Color]::White)

$titleFont = New-Object System.Drawing.Font("Segoe UI", 30, [System.Drawing.FontStyle]::Bold)
$subtitleFont = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Regular)
$axisFont = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Regular)
$axisTitleFont = New-Object System.Drawing.Font("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)
$legendFont = New-Object System.Drawing.Font("Segoe UI", 15, [System.Drawing.FontStyle]::Regular)
$noteFont = New-Object System.Drawing.Font("Segoe UI", 13, [System.Drawing.FontStyle]::Italic)
$textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(35, 39, 43))
$mutedBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(90, 99, 108))
$axisPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(80, 88, 96), 2)
$gridPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(220, 225, 230), 2)

try {
    $centerFormat = New-Object System.Drawing.StringFormat
    $centerFormat.Alignment = [System.Drawing.StringAlignment]::Center
    $centerFormat.LineAlignment = [System.Drawing.StringAlignment]::Center
    $rightFormat = New-Object System.Drawing.StringFormat
    $rightFormat.Alignment = [System.Drawing.StringAlignment]::Far
    $rightFormat.LineAlignment = [System.Drawing.StringAlignment]::Center

    $graphics.DrawString(
        "Tempo de busca por tamanho da frota e raio consultado",
        $titleFont,
        $textBrush,
        [System.Drawing.RectangleF]::new(60, 38, $width - 120, 55),
        $centerFormat
    )
    $graphics.DrawString(
        $subtitleText,
        $subtitleFont,
        $mutedBrush,
        [System.Drawing.RectangleF]::new(60, 98, $width - 120, 40),
        $centerFormat
    )

    $legendStartX = 260
    for ($index = 0; $index -lt $series.Count; $index++) {
        $item = $series[$index]
        $legendX = $legendStartX + $index * 360
        $legendY = 181
        $pen = New-Object System.Drawing.Pen($item.Color, 5)
        $pen.DashStyle = $item.Dash
        try {
            $graphics.DrawLine($pen, $legendX, $legendY, $legendX + 64, $legendY)
            Draw-Marker $graphics $item.Color $item.Marker ($legendX + 32) $legendY
            $graphics.DrawString($item.Label, $legendFont, $textBrush, $legendX + 80, $legendY - 17)
        }
        finally {
            $pen.Dispose()
        }
    }

    foreach ($tick in @(0, 5, 10, 15, 20)) {
        $y = Get-YCoordinate $tick
        $graphics.DrawLine($gridPen, $left, $y, $left + $plotWidth, $y)
        $graphics.DrawString(
            ([string]$tick),
            $axisFont,
            $textBrush,
            [System.Drawing.RectangleF]::new(60, $y - 20, $left - 80, 40),
            $rightFormat
        )
    }

    $graphics.DrawLine($axisPen, $left, $top, $left, $top + $plotHeight)
    $graphics.DrawLine($axisPen, $left, $top + $plotHeight, $left + $plotWidth, $top + $plotHeight)

    for ($index = 0; $index -lt $fleetLabels.Count; $index++) {
        $x = $xCoordinates[$index]
        $graphics.DrawLine($axisPen, $x, $top + $plotHeight, $x, $top + $plotHeight + 10)
        $graphics.DrawString(
            $fleetLabels[$index],
            $axisFont,
            $textBrush,
            [System.Drawing.RectangleF]::new($x - 90, $top + $plotHeight + 15, 180, 40),
            $centerFormat
        )
    }

    foreach ($item in $series) {
        $pen = New-Object System.Drawing.Pen($item.Color, 6)
        $pen.DashStyle = $item.Dash
        try {
            for ($index = 0; $index -lt 2; $index++) {
                $graphics.DrawLine(
                    $pen,
                    $xCoordinates[$index],
                    (Get-YCoordinate $item.Values[$index]),
                    $xCoordinates[$index + 1],
                    (Get-YCoordinate $item.Values[$index + 1])
                )
            }
            for ($index = 0; $index -lt 3; $index++) {
                Draw-Marker (
                    $graphics
                ) $item.Color $item.Marker $xCoordinates[$index] (Get-YCoordinate $item.Values[$index])
            }
        }
        finally {
            $pen.Dispose()
        }
    }

    $graphics.DrawString(
        $xAxisText,
        $axisTitleFont,
        $textBrush,
        [System.Drawing.RectangleF]::new($left, $height - 105, $plotWidth, 45),
        $centerFormat
    )

    $graphics.TranslateTransform(42, $top + $plotHeight / 2)
    $graphics.RotateTransform(-90)
    $graphics.DrawString(
        "Tempo da busca (ms)",
        $axisTitleFont,
        $textBrush,
        [System.Drawing.RectangleF]::new(-220, -25, 440, 50),
        $centerFormat
    )
    $graphics.ResetTransform()

    $graphics.DrawString(
        $sourceText,
        $noteFont,
        $mutedBrush,
        175,
        $height - 48
    )

    $destination = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath))
    $destinationDirectory = [System.IO.Path]::GetDirectoryName($destination)
    if (-not [System.IO.Directory]::Exists($destinationDirectory)) {
        [System.IO.Directory]::CreateDirectory($destinationDirectory) | Out-Null
    }
    $bitmap.Save($destination, [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output $destination
}
finally {
    $titleFont.Dispose()
    $subtitleFont.Dispose()
    $axisFont.Dispose()
    $axisTitleFont.Dispose()
    $legendFont.Dispose()
    $noteFont.Dispose()
    $textBrush.Dispose()
    $mutedBrush.Dispose()
    $axisPen.Dispose()
    $gridPen.Dispose()
    $graphics.Dispose()
    $bitmap.Dispose()
}
