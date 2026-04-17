package cs4201;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.en.EnglishAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.StringField;
import org.apache.lucene.document.TextField;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.search.similarities.BM25Similarity;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.MMapDirectory;

import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * CS4201 Information Retrieval — Java Lucene Indexer
 * Author : Shuvam Banerji Seal (22MS076)
 * Course Instructor : Dr. Dwaipayan Roy
 *
 * Reads JSONL corpus files and builds a Lucene index using:
 *   - EnglishAnalyzer (Porter stemming + stopword removal)
 *   - BM25Similarity  (k1 = 1.5, b = 0.4)
 *
 * Document field schema:
 *   docno           StringField  stored   — unique document ID
 *   collection      StringField  stored   — corpus name
 *   source_rel_path StringField  stored   — relative path within corpus
 *   title           TextField    stored   — article headline
 *   content         TextField    NOT stored — title + body (indexed only)
 *
 * Usage:
 *   java -cp java-lucene-ir-1.0-SNAPSHOT.jar cs4201.Indexer \
 *        [--index-dir <path>] [jsonl_file1 jsonl_file2 ...]
 */
public class Indexer {

    // BM25 parameters — k1 controls term-frequency saturation, b controls length normalisation.
    static final float BM25_K1 = 1.5f;
    static final float BM25_B  = 0.4f;

    // Default JSONL input paths, relative to the java_lucene_implementation/ directory.
    static final List<String> DEFAULT_JSONL_FILES = Arrays.asList(
        "../outputs/jsonl/combined_en_BDNews24.jsonl",
        "../outputs/jsonl/combined_en_TheTelegraph_2001_2010.jsonl"
    );

    // Output directory for Lucene index segments.
    static final String DEFAULT_INDEX_DIR = "../outputs/indexes/java_lucene_en_docs";

    public static void main(String[] args) throws Exception {
        String indexDir = DEFAULT_INDEX_DIR;
        List<String> jsonlFiles = new ArrayList<>(DEFAULT_JSONL_FILES);

        // Parse optional command-line arguments.
        List<String> extraFiles = new ArrayList<>();
        for (int i = 0; i < args.length; i++) {
            if ("--index-dir".equals(args[i]) && i + 1 < args.length) {
                indexDir = args[++i];
            } else if (!args[i].startsWith("--")) {
                extraFiles.add(args[i]);
            }
        }
        if (!extraFiles.isEmpty()) {
            jsonlFiles = extraFiles;
        }

        Path indexPath = Paths.get(indexDir).toAbsolutePath().normalize();
        Files.createDirectories(indexPath);

        System.out.println("[CS4201-Java-Indexer] BM25 k1=" + BM25_K1 + "  b=" + BM25_B);
        System.out.println("[CS4201-Java-Indexer] Index directory: " + indexPath);

        // EnglishAnalyzer applies Porter stemming and removes English stopwords.
        Analyzer analyzer = new EnglishAnalyzer();

        BM25Similarity similarity = new BM25Similarity(BM25_K1, BM25_B);

        // MMapDirectory uses memory-mapped I/O for efficient index access.
        Directory directory = MMapDirectory.open(indexPath);
        IndexWriterConfig config = new IndexWriterConfig(analyzer);
        config.setOpenMode(IndexWriterConfig.OpenMode.CREATE);
        config.setSimilarity(similarity);

        long indexed = 0L;
        long skipped = 0L;

        try (IndexWriter writer = new IndexWriter(directory, config)) {

            for (String jsonlFilePath : jsonlFiles) {
                Path filePath = resolveRelativePath(jsonlFilePath);

                if (!Files.exists(filePath)) {
                    System.err.println("[WARN] JSONL file missing, skipping: " + filePath);
                    continue;
                }

                System.out.println("[CS4201-Java-Indexer] Reading: " + filePath);

                // Stream line-by-line to avoid loading the full corpus into memory.
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(
                                new FileInputStream(filePath.toFile()), StandardCharsets.UTF_8))) {

                    String line;
                    int lineNo = 0;

                    while ((line = reader.readLine()) != null) {
                        lineNo++;
                        line = line.trim();
                        if (line.isEmpty()) continue;

                        // Parse the JSON object from this line.
                        JsonObject obj;
                        try {
                            obj = JsonParser.parseString(line).getAsJsonObject();
                        } catch (Exception e) {
                            System.err.println("[WARN] JSON parse error at line " + lineNo
                                    + " in " + filePath.getFileName() + ": " + e.getMessage());
                            skipped++;
                            continue;
                        }

                        String docno   = normalizeText(getStr(obj, "docno"));
                        String title   = normalizeText(getStr(obj, "title"));
                        // Check "text" first, fall back to "content".
                        String rawText = obj.has("text") ? getStr(obj, "text") : getStr(obj, "content");
                        String content = normalizeText(rawText);
                        String collection    = normalizeText(getStr(obj, "collection"));
                        String sourceRelPath = normalizeText(getStr(obj, "source_rel_path"));

                        if (docno.isEmpty() || content.isEmpty()) {
                            skipped++;
                            continue;
                        }

                        Document doc = new Document();
                        doc.add(new StringField("docno",            docno,          Field.Store.YES));
                        doc.add(new StringField("collection",       collection,     Field.Store.YES));
                        doc.add(new StringField("source_rel_path",  sourceRelPath,  Field.Store.YES));
                        doc.add(new TextField(  "title",            title,          Field.Store.YES));

                        // Concatenate title and body into the content field so title
                        // terms also contribute to content-field BM25 scores.
                        String fullContent = (title + " " + content).trim();
                        doc.add(new TextField("content", fullContent, Field.Store.NO));

                        writer.addDocument(doc);
                        indexed++;

                        if (indexed % 10_000 == 0) {
                            System.out.println("[CS4201-Java-Indexer] Indexed " + indexed
                                    + " documents...");
                        }
                    }
                }
            }

            writer.commit();

        }

        directory.close();

        System.out.println("\n=== INDEXING COMPLETE ===");
        System.out.println("index_dir:    " + indexPath);
        System.out.println("indexed_docs: " + indexed);
        System.out.println("skipped_docs: " + skipped);
    }

    // ---------------------------------------------------------------------------
    // Utilities (package-visible — also used by Retriever.java)
    // ---------------------------------------------------------------------------

    /** Collapse whitespace and trim. */
    static String normalizeText(String value) {
        if (value == null || value.isEmpty()) return "";
        return value.replaceAll("\\s+", " ").trim();
    }

    /** Returns the string value of a JSON key, or "" if missing or null. */
    static String getStr(JsonObject obj, String key) {
        if (!obj.has(key) || obj.get(key).isJsonNull()) return "";
        return obj.get(key).getAsString();
    }

    /**
     * Resolves a path against the current working directory if relative,
     * or returns it unchanged if absolute.
     */
    static Path resolveRelativePath(String pathStr) {
        Path p = Paths.get(pathStr);
        if (p.isAbsolute()) return p.normalize();
        return Paths.get("").toAbsolutePath().resolve(p).normalize();
    }
}
