# App Integration Guide: Retrieving Keyboard Layouts

This document describes how to implement the retrieval and management of keyboard layout JSON files in your Android application.

## Overview

The app needs to:
1. Fetch the layouts manifest from GitHub Pages
2. Parse available layouts
3. Download selected layout JSON files
4. Cache layouts locally
5. Handle updates and verification

## Manifest URL

The layouts manifest is served via GitHub Pages at:
```
https://{owner}.github.io/{repo}/layouts-manifest.json
```

For this repository:
```
https://palsoftware.github.io/pastiera-dict/layouts-manifest.json
```

## Manifest Structure

The manifest is a JSON object with the following structure:

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-01-15T18:20:29.135887Z",
  "releaseTag": "1",
  "items": [
    {
      "id": "qwerty",
      "filename": "qwerty.json",
      "url": "https://github.com/.../releases/download/1/qwerty.json",
      "bytes": 1579,
      "sha256": "7c3c05e9f1465cc73ff0395d2f7db27d56f58731a5fd7f5d18ea0efa5f2a5b3",
      "updatedAt": "2026-01-15T18:20:05.340413Z",
      "name": "QWERTY",
      "shortDescription": "Standard QWERTY keyboard layout",
      "languageTag": ""
    }
  ]
}
```

### Data Models

#### Manifest Model

```kotlin
data class LayoutsManifest(
    val schemaVersion: Int,
    val generatedAt: String,
    val releaseTag: String,
    val items: List<LayoutItem>
)

data class LayoutItem(
    val id: String,
    val filename: String,
    val url: String,
    val bytes: Long,
    val sha256: String,
    val updatedAt: String,
    val name: String,
    val shortDescription: String,
    val languageTag: String
)
```

#### Layout JSON Model

The downloaded layout JSON has this structure:

```json
{
  "name": "QWERTY",
  "description": "Standard QWERTY keyboard layout",
  "mappings": {
    "KEYCODE_Q": { "lowercase": "q", "uppercase": "Q" },
    "KEYCODE_W": { "lowercase": "w", "uppercase": "W" },
    ...
  }
}
```

```kotlin
data class KeyboardLayout(
    val name: String,
    val description: String,
    val mappings: Map<String, KeyMapping>
)

data class KeyMapping(
    val lowercase: String,
    val uppercase: String
)
```

## Implementation Steps

### Step 1: Fetch Manifest

Fetch the manifest from GitHub Pages using HTTP client.

**Kotlin Example (using OkHttp):**

```kotlin
import okhttp3.OkHttpClient
import okhttp3.Request
import com.google.gson.Gson
import java.io.IOException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class LayoutManifestService(
    private val httpClient: OkHttpClient,
    private val gson: Gson
) {
    private val manifestUrl = "https://palsoftware.github.io/pastiera-dict/layouts-manifest.json"
    
    suspend fun fetchManifest(): Result<LayoutsManifest> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url(manifestUrl)
                .get()
                .build()
            
            val response = httpClient.newCall(request).execute()
            
            if (!response.isSuccessful) {
                return@withContext Result.failure(
                    IOException("Failed to fetch manifest: ${response.code}")
                )
            }
            
            val json = response.body?.string() ?: ""
            val manifest = gson.fromJson(json, LayoutsManifest::class.java)
            
            Result.success(manifest)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
```

**Alternative: Using Retrofit**

```kotlin
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET

interface LayoutManifestApi {
    @GET("layouts-manifest.json")
    suspend fun getManifest(): LayoutsManifest
}

// Setup
val retrofit = Retrofit.Builder()
    .baseUrl("https://palsoftware.github.io/pastiera-dict/")
    .addConverterFactory(GsonConverterFactory.create())
    .build()

val api = retrofit.create(LayoutManifestApi::class.java)
```

### Step 2: Parse and Display Available Layouts

Once you have the manifest, you can display available layouts to the user:

```kotlin
fun getAvailableLayouts(manifest: LayoutsManifest): List<LayoutItem> {
    return manifest.items.sortedBy { it.name }
}

// Display in UI
fun displayLayouts(layouts: List<LayoutItem>) {
    layouts.forEach { layout ->
        println("${layout.name}: ${layout.shortDescription}")
        println("  ID: ${layout.id}")
        println("  Size: ${layout.bytes} bytes")
        println("  Updated: ${layout.updatedAt}")
    }
}
```

### Step 3: Download Layout JSON

Download the layout JSON file from the GitHub Release URL.

**Kotlin Example:**

```kotlin
class LayoutDownloadService(
    private val httpClient: OkHttpClient,
    private val gson: Gson
) {
    suspend fun downloadLayout(item: LayoutItem): Result<KeyboardLayout> = 
        withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url(item.url)
                .get()
                .build()
            
            val response = httpClient.newCall(request).execute()
            
            if (!response.isSuccessful) {
                return@withContext Result.failure(
                    IOException("Failed to download layout: ${response.code}")
                )
            }
            
            val json = response.body?.string() ?: ""
            val layout = gson.fromJson(json, KeyboardLayout::class.java)
            
            Result.success(layout)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
```

### Step 4: Verify SHA-256 (Recommended)

Verify the downloaded file matches the expected SHA-256 hash to ensure integrity:

```kotlin
import java.security.MessageDigest

fun verifySha256(data: ByteArray, expectedHash: String): Boolean {
    val digest = MessageDigest.getInstance("SHA-256")
    val hashBytes = digest.digest(data)
    val hashString = hashBytes.joinToString("") { "%02x".format(it) }
    return hashString.equals(expectedHash, ignoreCase = true)
}

// Usage
suspend fun downloadAndVerifyLayout(item: LayoutItem): Result<KeyboardLayout> = 
    withContext(Dispatchers.IO) {
    try {
        val request = Request.Builder()
            .url(item.url)
            .get()
            .build()
        
        val response = httpClient.newCall(request).execute()
        
        if (!response.isSuccessful) {
            return@withContext Result.failure(
                IOException("Failed to download: ${response.code}")
            )
        }
        
        val data = response.body?.bytes() ?: byteArrayOf()
        
        // Verify SHA-256
        if (!verifySha256(data, item.sha256)) {
            return@withContext Result.failure(
                SecurityException("SHA-256 verification failed")
            )
        }
        
        // Parse JSON
        val json = String(data, Charsets.UTF_8)
        val layout = gson.fromJson(json, KeyboardLayout::class.java)
        
        Result.success(layout)
    } catch (e: Exception) {
        Result.failure(e)
    }
}
```

### Step 5: Local Caching

Cache downloaded layouts locally to avoid repeated downloads.

**Using Room Database:**

```kotlin
import androidx.room.*

@Entity(tableName = "cached_layouts")
data class CachedLayout(
    @PrimaryKey val id: String,
    val layoutJson: String,
    val sha256: String,
    val downloadedAt: Long,
    val updatedAt: String
)

@Dao
interface CachedLayoutDao {
    @Query("SELECT * FROM cached_layouts WHERE id = :id")
    suspend fun getById(id: String): CachedLayout?
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(layout: CachedLayout)
    
    @Query("DELETE FROM cached_layouts WHERE id = :id")
    suspend fun delete(id: String)
}

// Usage
class LayoutCacheRepository(
    private val dao: CachedLayoutDao,
    private val gson: Gson
) {
    suspend fun getLayout(id: String): KeyboardLayout? {
        val cached = dao.getById(id)
        return cached?.let {
            gson.fromJson(it.layoutJson, KeyboardLayout::class.java)
        }
    }
    
    suspend fun saveLayout(id: String, layout: KeyboardLayout, sha256: String) {
        val json = gson.toJson(layout)
        val cached = CachedLayout(
            id = id,
            layoutJson = json,
            sha256 = sha256,
            downloadedAt = System.currentTimeMillis(),
            updatedAt = ""
        )
        dao.insert(cached)
    }
}
```

**Alternative: Using File Storage**

```kotlin
import android.content.Context
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class FileLayoutCache(
    private val context: Context,
    private val gson: Gson
) {
    private fun getCacheFile(id: String): File {
        val cacheDir = File(context.cacheDir, "layouts")
        cacheDir.mkdirs()
        return File(cacheDir, "$id.json")
    }
    
    suspend fun getLayout(id: String): KeyboardLayout? = withContext(Dispatchers.IO) {
        val file = getCacheFile(id)
        if (!file.exists()) return@withContext null
        
        try {
            val json = file.readText()
            gson.fromJson(json, KeyboardLayout::class.java)
        } catch (e: Exception) {
            null
        }
    }
    
    suspend fun saveLayout(id: String, layout: KeyboardLayout) = 
        withContext(Dispatchers.IO) {
        val file = getCacheFile(id)
        val json = gson.toJson(layout)
        file.writeText(json)
    }
}
```

### Step 6: Check for Updates

Check if a cached layout needs updating by comparing `updatedAt` timestamps:

```kotlin
import java.time.Instant

class LayoutUpdateChecker(
    private val cacheRepository: LayoutCacheRepository
) {
    suspend fun needsUpdate(item: LayoutItem): Boolean {
        val cached = cacheRepository.getCachedMetadata(item.id)
        
        if (cached == null) {
            return true // Not cached, needs download
        }
        
        // Compare updatedAt timestamps
        val cachedTime = Instant.parse(cached.updatedAt)
        val manifestTime = Instant.parse(item.updatedAt)
        
        return manifestTime.isAfter(cachedTime)
    }
}
```

### Step 7: Complete Flow

Combine all steps into a complete service:

```kotlin
class LayoutService(
    private val manifestService: LayoutManifestService,
    private val downloadService: LayoutDownloadService,
    private val cacheRepository: LayoutCacheRepository,
    private val updateChecker: LayoutUpdateChecker
) {
    suspend fun getLayout(layoutId: String): Result<KeyboardLayout> {
        // 1. Fetch manifest
        val manifestResult = manifestService.fetchManifest()
        val manifest = manifestResult.getOrElse {
            return Result.failure(it)
        }
        
        // 2. Find layout in manifest
        val item = manifest.items.find { it.id == layoutId }
            ?: return Result.failure(IllegalArgumentException("Layout not found: $layoutId"))
        
        // 3. Check cache
        val cached = cacheRepository.getLayout(layoutId)
        if (cached != null && !updateChecker.needsUpdate(item)) {
            return Result.success(cached)
        }
        
        // 4. Download and verify
        val downloadResult = downloadService.downloadAndVerifyLayout(item)
        val layout = downloadResult.getOrElse {
            // If download fails, return cached version if available
            return if (cached != null) {
                Result.success(cached)
            } else {
                Result.failure(it)
            }
        }
        
        // 5. Save to cache
        cacheRepository.saveLayout(layoutId, layout, item.sha256)
        
        return Result.success(layout)
    }
    
    suspend fun getAllAvailableLayouts(): Result<List<LayoutItem>> {
        val manifestResult = manifestService.fetchManifest()
        return manifestResult.map { it.items }
    }
}
```

## Error Handling

### Network Errors

```kotlin
sealed class LayoutError {
    object NetworkError : LayoutError()
    object NotFound : LayoutError()
    object VerificationFailed : LayoutError()
    data class Unknown(val exception: Exception) : LayoutError()
}

fun handleError(exception: Exception): LayoutError {
    return when (exception) {
        is IOException -> LayoutError.NetworkError
        is SecurityException -> LayoutError.VerificationFailed
        is IllegalArgumentException -> LayoutError.NotFound
        else -> LayoutError.Unknown(exception)
    }
}
```

### Retry Logic

```kotlin
import kotlinx.coroutines.delay

suspend fun <T> retry(
    times: Int = 3,
    delay: Long = 1000,
    block: suspend () -> Result<T>
): Result<T> {
    repeat(times - 1) {
        val result = block()
        if (result.isSuccess) return result
        delay(delay * (it + 1)) // Exponential backoff
    }
    return block()
}

// Usage
val layout = retry {
    layoutService.getLayout("qwerty")
}
```

## Background Updates

Use WorkManager to periodically check for layout updates:

```kotlin
import androidx.work.*
import kotlinx.coroutines.*

class LayoutUpdateWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {
    
    override suspend fun doWork(): Result {
        return try {
            val manifestService = LayoutManifestService(...)
            val manifest = manifestService.fetchManifest().getOrThrow()
            
            // Check for updates and download if needed
            // ...
            
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }
}

// Schedule periodic updates
val workRequest = PeriodicWorkRequestBuilder<LayoutUpdateWorker>(
    1, TimeUnit.DAYS
).build()

WorkManager.getInstance(context).enqueue(workRequest)
```

## UI Integration Example

```kotlin
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.*

class LayoutSelectionViewModel(
    private val layoutService: LayoutService
) : ViewModel() {
    
    private val _layouts = MutableStateFlow<List<LayoutItem>>(emptyList())
    val layouts: StateFlow<List<LayoutItem>> = _layouts.asStateFlow()
    
    private val _loading = MutableStateFlow(false)
    val loading: StateFlow<Boolean> = _loading.asStateFlow()
    
    fun loadLayouts() {
        viewModelScope.launch {
            _loading.value = true
            val result = layoutService.getAllAvailableLayouts()
            result.onSuccess { items ->
                _layouts.value = items
            }.onFailure { error ->
                // Handle error
            }
            _loading.value = false
        }
    }
    
    fun selectLayout(layoutId: String) {
        viewModelScope.launch {
            val result = layoutService.getLayout(layoutId)
            result.onSuccess { layout ->
                // Apply layout to keyboard
            }.onFailure { error ->
                // Show error message
            }
        }
    }
}
```

## Best Practices

1. **Always verify SHA-256** - Ensures file integrity and security
2. **Cache layouts locally** - Reduces network usage and improves performance
3. **Check for updates** - Compare `updatedAt` timestamps before downloading
4. **Handle errors gracefully** - Fall back to cached versions when possible
5. **Use background updates** - Periodically check for new layouts
6. **Show loading states** - Provide user feedback during downloads
7. **Respect network conditions** - Only download on WiFi if configured
8. **Validate JSON structure** - Handle schema changes gracefully

## Performance Considerations

- **Manifest size**: Small (~10-20 KB), can be cached for extended periods
- **Layout size**: Small (~1-5 KB per layout), quick to download
- **Concurrent downloads**: Limit concurrent downloads to avoid overwhelming the network
- **Cache expiration**: Consider expiring cached layouts after a period (e.g., 7 days)

## Testing

### Unit Tests

```kotlin
import org.junit.Test
import org.junit.Assert.*

@Test
fun testManifestParsing() {
    val json = """
    {
      "schemaVersion": 1,
      "generatedAt": "2026-01-15T18:20:29.135887Z",
      "releaseTag": "1",
      "items": []
    }
    """.trimIndent()
    
    val manifest = gson.fromJson(json, LayoutsManifest::class.java)
    assertEquals(1, manifest.schemaVersion)
    assertTrue(manifest.items.isNotEmpty())
}
```

### Integration Tests

```kotlin
import kotlinx.coroutines.test.runTest

@Test
fun testLayoutDownload() = runTest {
    val service = LayoutDownloadService(httpClient, gson)
    val item = LayoutItem(
        id = "qwerty",
        url = "https://...",
        // ...
    )
    
    val result = service.downloadAndVerifyLayout(item)
    assertTrue(result.isSuccess)
}
```

## Security Considerations

1. **HTTPS only** - All downloads should use HTTPS
2. **SHA-256 verification** - Always verify downloaded files
3. **Input validation** - Validate JSON structure before parsing
4. **Sandboxing** - Store cached files in app-specific directories
5. **Certificate pinning** - Consider pinning GitHub certificates for production

## Migration and Schema Changes

Handle schema version changes:

```kotlin
fun handleSchemaVersion(manifest: LayoutsManifest) {
    when (manifest.schemaVersion) {
        1 -> {
            // Current schema, proceed normally
        }
        else -> {
            // Unknown schema version, handle gracefully
            // Could show error or attempt to parse with fallback
        }
    }
}
```

## Complete Example Repository Structure

A complete example implementation would include:

```
app/
├── data/
│   ├── model/
│   │   ├── LayoutsManifest.kt
│   │   ├── LayoutItem.kt
│   │   └── KeyboardLayout.kt
│   ├── remote/
│   │   ├── LayoutManifestApi.kt
│   │   └── LayoutDownloadService.kt
│   ├── local/
│   │   ├── LayoutCacheRepository.kt
│   │   └── CachedLayout.kt
│   └── LayoutService.kt
├── ui/
│   └── LayoutSelectionViewModel.kt
└── worker/
    └── LayoutUpdateWorker.kt
```

This structure provides separation of concerns and makes testing easier.
