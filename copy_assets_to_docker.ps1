# Copy images and chapters to the Docker container
Write-Host "Copying images and chapters to Docker container..."

# Create directories in the container
docker exec -it esd-weebs-app mkdir -p /app/images
docker exec -it esd-weebs-app mkdir -p /app/Chapters

# Copy images directory
Write-Host "Copying images..."
Get-ChildItem "./images" -File | ForEach-Object {
    $sourceFile = $_.FullName
    $destFile = "/app/images/$($_.Name)"
    Write-Host "Copying $sourceFile to $destFile"
    docker cp $sourceFile esd-weebs-app:$destFile
}

# Copy chapters directories
Write-Host "Copying chapters..."
Get-ChildItem "./Chapters" -Directory | ForEach-Object {
    $comicName = $_.Name
    Write-Host "Copying comic: $comicName"
    
    # Create comic directory in container
    docker exec -it esd-weebs-app mkdir -p "/app/Chapters/$comicName"
    
    # Get all chapter folders
    Get-ChildItem "$($_.FullName)" -Directory | ForEach-Object {
        $chapterName = $_.Name
        Write-Host "  Copying chapter: $chapterName"
        
        # Create chapter directory in container
        docker exec -it esd-weebs-app mkdir -p "/app/Chapters/$comicName/$chapterName"
        
        # Copy all images in this chapter
        Get-ChildItem "$($_.FullName)" -File | ForEach-Object {
            $sourceFile = $_.FullName
            $destFile = "/app/Chapters/$comicName/$chapterName/$($_.Name)"
            Write-Host "    Copying image: $($_.Name)"
            docker cp $sourceFile esd-weebs-app:$destFile
        }
    }
}

Write-Host "All assets copied to Docker container."
Write-Host "Now run the upload script with:"
Write-Host "docker exec -it esd-weebs-app python upload_chapter_pages.py" 