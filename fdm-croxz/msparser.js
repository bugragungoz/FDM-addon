/**
 * Croxz Universal Parser
 * Supports media extraction via yt-dlp and direct file downloads
 * Version: 1.1.0
 */

var msParser = (function() {
    
    // Direct download file extensions
    var ARCHIVE_EXT = ["zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "cab", "lzh", "arj"];
    var EXECUTABLE_EXT = ["exe", "msi", "dmg", "pkg", "deb", "rpm", "appimage", "apk", "ipa", "run", "bin"];
    var DOCUMENT_EXT = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "epub", "mobi", "djvu"];
    var IMAGE_EXT = ["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "ico", "tiff", "psd", "raw", "heic"];
    var AUDIO_EXT = ["mp3", "m4a", "wav", "flac", "ogg", "aac", "wma", "opus", "alac", "aiff"];
    var VIDEO_EXT = ["mp4", "mkv", "webm", "avi", "mov", "wmv", "flv", "m4v", "ts", "m2ts", "vob", "3gp"];
    var FONT_EXT = ["ttf", "otf", "woff", "woff2", "eot"];
    var CODE_EXT = ["js", "py", "java", "cpp", "c", "cs", "php", "rb", "go", "rs", "swift", "kt"];
    var DATA_EXT = ["json", "xml", "yaml", "yml", "sql", "db", "sqlite", "csv", "tsv"];
    
    var ALL_DIRECT_EXT = [].concat(
        ARCHIVE_EXT, EXECUTABLE_EXT, DOCUMENT_EXT, IMAGE_EXT,
        AUDIO_EXT, VIDEO_EXT, FONT_EXT, CODE_EXT, DATA_EXT
    );
    
    // Media site patterns (for yt-dlp) - Extended list
    var MEDIA_PATTERNS = [
        // Major platforms
        /^https?:\/\/(www\.)?(youtube\.com|youtu\.be)\//i,
        /^https?:\/\/(www\.)?(twitter\.com|x\.com)\//i,
        /^https?:\/\/(www\.)?instagram\.com\//i,
        /^https?:\/\/(www\.)?tiktok\.com\//i,
        /^https?:\/\/(www\.)?vimeo\.com\//i,
        /^https?:\/\/(www\.)?dailymotion\.com\//i,
        /^https?:\/\/(www\.)?twitch\.tv\//i,
        /^https?:\/\/(www\.)?facebook\.com\//i,
        /^https?:\/\/(www\.)?reddit\.com\//i,
        /^https?:\/\/(www\.)?v\.redd\.it\//i,
        // Audio platforms
        /^https?:\/\/(www\.)?soundcloud\.com\//i,
        /^https?:\/\/(www\.)?bandcamp\.com\//i,
        /^https?:\/\/(www\.)?mixcloud\.com\//i,
        /^https?:\/\/(www\.)?audiomack\.com\//i,
        // Asian platforms
        /^https?:\/\/(www\.)?bilibili\.com\//i,
        /^https?:\/\/(www\.)?nicovideo\.jp\//i,
        /^https?:\/\/(www\.)?weibo\.com\//i,
        /^https?:\/\/(www\.)?douyin\.com\//i,
        // Alternative platforms
        /^https?:\/\/(www\.)?rumble\.com\//i,
        /^https?:\/\/(www\.)?odysee\.com\//i,
        /^https?:\/\/(www\.)?bitchute\.com\//i,
        /^https?:\/\/(www\.)?peertube\./i,
        /^https?:\/\/(www\.)?dtube\.video\//i,
        // Social/Messaging
        /^https?:\/\/(www\.)?vk\.com\//i,
        /^https?:\/\/(www\.)?ok\.ru\//i,
        /^https?:\/\/(t\.me|telegram\.me)\//i,
        // Streaming/Clips
        /^https?:\/\/(www\.)?streamable\.com\//i,
        /^https?:\/\/(www\.)?clips\.twitch\.tv\//i,
        /^https?:\/\/(www\.)?medal\.tv\//i,
        /^https?:\/\/(www\.)?streamja\.com\//i,
        /^https?:\/\/(www\.)?clippituser\.tv\//i,
        // News/Media
        /^https?:\/\/(www\.)?cnn\.com\//i,
        /^https?:\/\/(www\.)?bbc\.co\.uk\//i,
        /^https?:\/\/(www\.)?nytimes\.com\//i,
        /^https?:\/\/(www\.)?theguardian\.com\//i,
        // Education
        /^https?:\/\/(www\.)?ted\.com\//i,
        /^https?:\/\/(www\.)?coursera\.org\//i,
        /^https?:\/\/(www\.)?udemy\.com\//i,
        // Misc
        /^https?:\/\/(www\.)?gfycat\.com\//i,
        /^https?:\/\/(www\.)?imgur\.com\//i,
        /^https?:\/\/(www\.)?giphy\.com\//i,
        /^https?:\/\/(www\.)?coub\.com\//i,
        /^https?:\/\/(www\.)?vine\.co\//i,
        /^https?:\/\/(www\.)?flickr\.com\//i
    ];
    
    // Character replacements for filename sanitization
    var CHAR_REPLACEMENTS = {
        // Turkish
        '\u011f': 'g', '\u011e': 'G',
        '\u0131': 'i', '\u0130': 'I',
        '\u015f': 's', '\u015e': 'S',
        '\u00fc': 'u', '\u00dc': 'U',
        '\u00f6': 'o', '\u00d6': 'O',
        '\u00e7': 'c', '\u00c7': 'C',
        // German
        '\u00e4': 'ae', '\u00c4': 'Ae',
        '\u00df': 'ss',
        // French/Spanish
        '\u00e9': 'e', '\u00e8': 'e', '\u00ea': 'e',
        '\u00e0': 'a', '\u00e1': 'a', '\u00e2': 'a',
        '\u00f1': 'n', '\u00d1': 'N',
        // Symbols
        '\u2019': '', '\u2018': '',
        '\u201c': '', '\u201d': '',
        '\u2013': '-', '\u2014': '-',
        '\u2026': '...'
    };
    
    /**
     * Sanitize a string to be safe for use as a filename
     */
    function sanitizeFilename(str, maxLength) {
        if (!str) return "download";
        maxLength = maxLength || 200;
        
        var result = str;
        
        // Apply character replacements
        for (var char in CHAR_REPLACEMENTS) {
            if (CHAR_REPLACEMENTS.hasOwnProperty(char)) {
                result = result.split(char).join(CHAR_REPLACEMENTS[char]);
            }
        }
        
        // Remove non-ASCII characters
        result = result.replace(/[^\x00-\x7F]/g, '');
        
        // Remove invalid filename characters: \ / : * ? " < > |
        result = result.replace(/[\\/:*?"<>|]/g, '');
        
        // Replace multiple spaces/underscores with single underscore
        result = result.replace(/[\s_]+/g, '_');
        
        // Remove leading/trailing underscores and dots
        result = result.replace(/^[_.\s]+|[_.\s]+$/g, '');
        
        // Limit length
        if (result.length > maxLength) {
            result = result.substring(0, maxLength).replace(/_+$/, '');
        }
        
        return result || "download";
    }
    
    function getExtensionFromUrl(url) {
        try {
            var path = url.split("?")[0].split("#")[0];
            var parts = path.split("/");
            var filename = parts[parts.length - 1];
            if (filename.indexOf(".") !== -1) {
                var ext = filename.split(".").pop().toLowerCase();
                if (ext.length <= 10 && /^[a-z0-9]+$/.test(ext)) {
                    return ext;
                }
            }
        } catch (e) {
            console.error("[Croxz] getExtensionFromUrl error: " + e.message);
        }
        return null;
    }
    
    function getFilenameFromUrl(url) {
        try {
            var path = url.split("?")[0].split("#")[0];
            var parts = path.split("/");
            var filename = decodeURIComponent(parts[parts.length - 1]);
            return filename || "download";
        } catch (e) {
            console.error("[Croxz] getFilenameFromUrl error: " + e.message);
            return "download";
        }
    }
    
    function isDirectDownloadUrl(url) {
        var ext = getExtensionFromUrl(url);
        if (!ext) return false;
        return ALL_DIRECT_EXT.indexOf(ext) !== -1;
    }
    
    function isMediaSite(url) {
        for (var i = 0; i < MEDIA_PATTERNS.length; i++) {
            if (MEDIA_PATTERNS[i].test(url)) {
                return true;
            }
        }
        return false;
    }
    
    function getFileCategory(ext) {
        if (ARCHIVE_EXT.indexOf(ext) !== -1) return "archive";
        if (EXECUTABLE_EXT.indexOf(ext) !== -1) return "executable";
        if (DOCUMENT_EXT.indexOf(ext) !== -1) return "document";
        if (IMAGE_EXT.indexOf(ext) !== -1) return "image";
        if (AUDIO_EXT.indexOf(ext) !== -1) return "audio";
        if (VIDEO_EXT.indexOf(ext) !== -1) return "video";
        if (FONT_EXT.indexOf(ext) !== -1) return "font";
        if (CODE_EXT.indexOf(ext) !== -1) return "code";
        if (DATA_EXT.indexOf(ext) !== -1) return "data";
        return "file";
    }
    
    function MsParser() {}
    
    MsParser.prototype = {
        
        parse: function(obj) {
            var self = this;
            var url = obj.url;
            
            console.log("[Croxz] Parsing URL: " + url);
            
            // Check if direct download
            if (isDirectDownloadUrl(url)) {
                console.log("[Croxz] Direct download detected");
                return self.createDirectDownloadResult(url);
            }
            
            // Use Python bridge for extraction
            return launchPythonScript(
                obj.requestId,
                obj.interactive,
                "croxz_bridge.py",
                ["extract", url]
            ).then(function(result) {
                return self.processResult(result, url);
            });
        },
        
        createDirectDownloadResult: function(url) {
            return new Promise(function(resolve, reject) {
                try {
                    var rawFilename = getFilenameFromUrl(url);
                    var ext = getExtensionFromUrl(url) || "bin";
                    var category = getFileCategory(ext);
                    var protocol = url.indexOf("https") === 0 ? "https" : "http";
                    
                    // Clean filename - remove extension, sanitize, then use
                    var nameWithoutExt = rawFilename;
                    if (rawFilename.indexOf(".") !== -1) {
                        nameWithoutExt = rawFilename.substring(0, rawFilename.lastIndexOf("."));
                    }
                    var cleanName = sanitizeFilename(nameWithoutExt);
                    
                    var fmt = {
                        url: url,
                        protocol: protocol,
                        ext: ext,
                        format: category + "/" + ext
                    };
                    
                    // Set appropriate ext fields
                    if (category === "video") {
                        fmt.video_ext = ext;
                    } else if (category === "audio") {
                        fmt.audio_ext = ext;
                    }
                    
                    var result = {
                        id: cleanName,
                        title: cleanName,
                        webpage_url: url,
                        formats: [fmt]
                    };
                    
                    console.log("[Croxz] Direct download: " + cleanName + "." + ext + " (" + category + ")");
                    resolve(result);
                    
                } catch (e) {
                    console.error("[Croxz] createDirectDownloadResult error: " + e.message);
                    reject({error: "Failed to process URL: " + e.message, isParseError: true});
                }
            });
        },
        
        processResult: function(result, url) {
            return new Promise(function(resolve, reject) {
                try {
                    if (result.exitCode !== 0) {
                        var errorMsg = result.errorOutput || result.output || "Extraction failed";
                        console.error("[Croxz] Exit code: " + result.exitCode + ", Error: " + errorMsg);
                        reject({error: errorMsg, isParseError: true});
                        return;
                    }
                    
                    var output = result.output.trim();
                    if (!output) {
                        reject({error: "No output from extractor", isParseError: true});
                        return;
                    }
                    
                    var data = JSON.parse(output);
                    
                    if (data.error) {
                        reject({error: data.error, isParseError: true});
                        return;
                    }
                    
                    if (!data.title) {
                        data.title = getFilenameFromUrl(url);
                    }
                    
                    if (!data.formats || data.formats.length === 0) {
                        reject({error: "No downloadable formats found", isParseError: true});
                        return;
                    }
                    
                    if (!data.webpage_url) {
                        data.webpage_url = url;
                    }
                    
                    console.log("[Croxz] Extracted: " + data.title + " (" + data.formats.length + " formats)");
                    resolve(data);
                    
                } catch (e) {
                    console.error("[Croxz] Parse error: " + e.message);
                    reject({error: "Failed to parse output: " + e.message, isParseError: true});
                }
            });
        },
        
        isSupportedSource: function(url) {
            // IMPORTANT: Do NOT handle direct file downloads (exe, zip, etc.)
            // Let FDM handle them natively - only process known media sites
            if (isDirectDownloadUrl(url)) {
                return false;
            }
            
            // Only support known media sites for yt-dlp extraction
            if (isMediaSite(url)) {
                return true;
            }
            
            return false;
        },
        
        supportedSourceCheckPriority: function() {
            // Lower priority so site-specific plugins take precedence
            return 50;
        },
        
        isPossiblySupportedSource: function(obj) {
            if (!/^https?:\/\//i.test(obj.url)) {
                return false;
            }
            
            // IMPORTANT: Do NOT intercept direct file downloads
            // FDM handles exe, zip, pdf, etc. natively - much better than our addon
            if (isDirectDownloadUrl(obj.url)) {
                return false;
            }
            
            var contentType = obj.contentType || "";
            
            // Skip binary/archive content - let FDM handle natively
            if (/application\/(octet-stream|x-|zip|rar|pdf|x-msdownload|x-executable)/i.test(contentType)) {
                return false;
            }
            
            // Only intercept video/audio content types
            if (/^(video|audio)\//i.test(contentType)) {
                return true;
            }
            
            // For HTML pages, only intercept if it's a known media site
            if (/text\/html/i.test(contentType)) {
                return isMediaSite(obj.url);
            }
            
            return false;
        },
        
        minIntevalBetweenQueryInfoDownloads: function() {
            return 300;
        },
        
        overrideUrlPolicy: function(url) {
            return /^https?:\/\//i.test(url);
        }
    };
    
    return new MsParser();
}());

