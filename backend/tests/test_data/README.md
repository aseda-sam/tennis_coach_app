# Test Data Directory

This directory contains test video files for integration testing.

## Required Test Video

### `test_tennis_video.mp4`
- **Purpose**: Real tennis video for testing the complete video processing pipeline
- **Requirements**:
  - Duration: 5-10 seconds (to keep tests fast)
  - Format: MP4
  - Content: Simple tennis scene (serve, rally, etc.)
  - Size: < 10MB (to keep repository size manageable)
  - Quality: Standard definition (720p or lower)

## Adding Test Videos

1. **Upload your test video** to this directory
2. **Name it** `test_tennis_video.mp4`
3. **Ensure it's small** and contains tennis content
4. **Commit the file** to the repository

## Test Behavior

- **With test video**: Tests will run full video processing pipeline
- **Without test video**: Tests will be skipped with a clear message
- **Cleanup**: Processed files are automatically cleaned up after tests

## Example Test Video Sources

- Record a short tennis clip with your phone
- Download a free tennis video from stock footage sites
- Create a simple tennis animation

## Important Notes

- **Keep it small**: Large files slow down CI and take up repository space
- **Keep it simple**: Complex videos may cause test failures
- **Tennis content**: Should contain actual tennis scenes for realistic testing
- **Public domain**: Ensure you have rights to use the video for testing
