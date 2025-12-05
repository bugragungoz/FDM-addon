/**
 * Croxz Universal Playlist Parser
 * Supports playlists and batch downloads
 * Version: 1.1.0
 */

var msBatchVideoParser = (function() {
    
    // Playlist URL patterns - Extended list
    var PLAYLIST_PATTERNS = [
        // YouTube
        /^https?:\/\/(www\.)?youtube\.com\/playlist\?/i,
        /^https?:\/\/(www\.)?youtube\.com\/(c|channel|user)\/[^\/]+\/(videos|playlists|streams)/i,
        /^https?:\/\/(www\.)?youtube\.com\/@[^\/]+\/(videos|playlists|streams|shorts)/i,
        /^https?:\/\/(www\.)?youtube\.com\/feed\/subscriptions/i,
        /^https?:\/\/(www\.)?youtube\.com\/feed\/history/i,
        // SoundCloud
        /^https?:\/\/(www\.)?soundcloud\.com\/[^\/]+\/sets\//i,
        /^https?:\/\/(www\.)?soundcloud\.com\/[^\/]+\/albums\//i,
        /^https?:\/\/(www\.)?soundcloud\.com\/[^\/]+\/tracks/i,
        /^https?:\/\/(www\.)?soundcloud\.com\/[^\/]+\/likes/i,
        // Vimeo
        /^https?:\/\/(www\.)?vimeo\.com\/album\//i,
        /^https?:\/\/(www\.)?vimeo\.com\/channels\//i,
        /^https?:\/\/(www\.)?vimeo\.com\/showcase\//i,
        // Twitch
        /^https?:\/\/(www\.)?twitch\.tv\/[^\/]+\/videos/i,
        /^https?:\/\/(www\.)?twitch\.tv\/[^\/]+\/clips/i,
        /^https?:\/\/(www\.)?twitch\.tv\/collections\//i,
        // Dailymotion
        /^https?:\/\/(www\.)?dailymotion\.com\/playlist\//i,
        /^https?:\/\/(www\.)?dailymotion\.com\/[^\/]+\/playlists/i,
        // Bilibili
        /^https?:\/\/(www\.)?bilibili\.com\/medialist\//i,
        /^https?:\/\/space\.bilibili\.com\/\d+\/video/i,
        /^https?:\/\/(www\.)?bilibili\.com\/bangumi\/play\//i,
        // Bandcamp
        /^https?:\/\/[^\/]+\.bandcamp\.com\/album\//i,
        /^https?:\/\/(www\.)?bandcamp\.com\/[^\/]+\/album\//i,
        // Others
        /^https?:\/\/(www\.)?mixcloud\.com\/[^\/]+\/playlists\//i,
        /^https?:\/\/(www\.)?reddit\.com\/user\/[^\/]+\/submitted/i,
        /^https?:\/\/(www\.)?instagram\.com\/[^\/]+\/reels/i,
        /^https?:\/\/(www\.)?tiktok\.com\/@[^\/]+$/i,
        /^https?:\/\/(www\.)?rumble\.com\/c\//i,
        /^https?:\/\/(www\.)?odysee\.com\/@[^\/]+$/i
    ];
    
    /**
     * Sanitize playlist title for display
     */
    function sanitizeTitle(str) {
        if (!str) return "Playlist";
        return str
            .replace(/[^\x00-\x7F]/g, '')
            .replace(/[\s_]+/g, ' ')
            .trim() || "Playlist";
    }
    
    function MsBatchVideoParser() {}
    
    MsBatchVideoParser.prototype = {
        
        parse: function(obj) {
            var self = this;
            console.log("[Croxz] Parsing playlist/batch: " + obj.url);
            
            return launchPythonScript(
                obj.requestId,
                obj.interactive,
                "croxz_bridge.py",
                ["playlist", obj.url]
            ).then(function(result) {
                return self.processResult(result, obj.url);
            });
        },
        
        processResult: function(result, url) {
            return new Promise(function(resolve, reject) {
                try {
                    if (result.exitCode !== 0) {
                        var errorMsg = result.errorOutput || result.output || "Extraction failed";
                        console.error("[Croxz] Playlist exit code: " + result.exitCode);
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
                    
                    // Handle single item result
                    if (data._type !== "playlist") {
                        data = {
                            _type: "playlist",
                            title: data.title || "Download",
                            webpage_url: url,
                            entries: [{
                                _type: "url",
                                url: data.webpage_url || url,
                                title: data.title || "Unknown"
                            }]
                        };
                    }
                    
                    if (!data.entries || data.entries.length === 0) {
                        reject({error: "No entries found", isParseError: true});
                        return;
                    }
                    
                    // Clean entries
                    data.entries = data.entries.filter(function(entry) {
                        return entry && entry.url;
                    }).map(function(entry) {
                        return {
                            _type: "url",
                            url: entry.url,
                            title: entry.title || "Unknown",
                            duration: entry.duration
                        };
                    });
                    
                    if (!data.webpage_url) {
                        data.webpage_url = url;
                    }
                    
                    console.log("[Croxz] Playlist: " + data.title + " (" + data.entries.length + " items)");
                    resolve(data);
                    
                } catch (e) {
                    console.error("[Croxz] Parse error: " + e.message);
                    reject({error: "Failed to parse: " + e.message, isParseError: true});
                }
            });
        },
        
        isSupportedSource: function(url) {
            for (var i = 0; i < PLAYLIST_PATTERNS.length; i++) {
                if (PLAYLIST_PATTERNS[i].test(url)) {
                    return true;
                }
            }
            return false;
        },
        
        supportedSourceCheckPriority: function() {
            return 50;
        },
        
        isPossiblySupportedSource: function(obj) {
            var url = obj.url.toLowerCase();
            
            // Skip direct file downloads - let FDM handle natively
            var directExts = [".exe", ".msi", ".zip", ".rar", ".7z", ".tar", ".gz", 
                              ".pdf", ".doc", ".docx", ".iso", ".dmg", ".pkg", ".deb"];
            for (var i = 0; i < directExts.length; i++) {
                if (url.indexOf(directExts[i]) !== -1) {
                    return false;
                }
            }
            
            // Common playlist/batch indicators - Extended list
            var indicators = [
                "playlist", "/videos", "/album", "/sets/",
                "/channel/", "/collection/", "/list/", "/gallery/",
                "/playlists", "/tracks", "/likes", "/streams",
                "/shorts", "/reels", "/clips", "/showcase",
                "/medialist", "/bangumi", "/feed/"
            ];
            
            for (var j = 0; j < indicators.length; j++) {
                if (url.indexOf(indicators[j]) !== -1) {
                    return true;
                }
            }
            
            // Check for user/channel pages that might have video lists
            if (/\/@[^\/]+\/?$/.test(url)) {
                return true;
            }
            
            return false;
        },
        
        minIntevalBetweenQueryInfoDownloads: function() {
            return 500;
        }
    };
    
    return new MsBatchVideoParser();
}());

