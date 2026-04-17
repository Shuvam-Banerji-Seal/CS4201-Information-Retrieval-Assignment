package cs4201;

import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.en.EnglishAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.StoredFields;
import org.apache.lucene.queryparser.classic.QueryParser;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.search.similarities.BM25Similarity;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.MMapDirectory;

import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import javax.xml.parsers.DocumentBuilderFactory;

import java.io.BufferedWriter;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * CS4201 Information Retrieval — Java Lucene Retriever
 * Author : Shuvam Banerji Seal (22MS076)
 * Course Instructor : Dr. Dwaipayan Roy
 *
 * Queries a Lucene index built by Indexer.java over FIRE 2012 English Ad-hoc topics
 * and writes a TREC-style 6-column TSV run file.
 *
 * Configuration:
 *   Similarity  : BM25(k1=1.5, b=0.4)
 *   Analyzer    : EnglishAnalyzer (Porter stemming + stopwords)
 *   Query mode  : title-only
 *   Operator    : OR
 *   Top-K       : 100 documents per topic
 *
 * Output format (tab-separated, 6 columns):
 *   QID   Q0   DOCID   RANK   SCORE   RUNNAME
 *
 * Usage (from java_lucene_implementation/ directory):
 *   java -cp target/java-lucene-ir-1.0-SNAPSHOT.jar cs4201.Retriever \
 *        [--index-dir <path>] [--topics-file <path>] [--output-run <path>] \
 *        [--run-name <name>] [--top-k <n>]
 */
public class Retriever {

    // BM25 parameters — k1 controls term-frequency saturation, b controls length normalisation.
    static final float BM25_K1 = 1.5f;
    static final float BM25_B  = 0.4f;

    // Default paths (relative to CWD = java_lucene_implementation/)
    static final String DEFAULT_INDEX_DIR  = "../outputs/indexes/java_lucene_en_docs";
    static final String DEFAULT_TOPICS     = "../data/fire2012/adhoc/topics/en.topics.176-225.2012.txt";
    static final String DEFAULT_OUTPUT     = "../outputs/runs/java_bm25_k1_1.5_b_0.4_Shuvam_Banerji_Seal_22MS076.tsv";
    static final String DEFAULT_RUN_NAME   = "shuvam_java_bm25";
    static final int    DEFAULT_TOP_K      = 100;

    // Topic record — holds the four FIRE topic fields.
    record Topic(String qid, String title, String desc, String narr) {}

    public static void main(String[] args) throws Exception {
        String indexDir   = DEFAULT_INDEX_DIR;
        String topicsFile = DEFAULT_TOPICS;
        String outputFile = DEFAULT_OUTPUT;
        String runName    = DEFAULT_RUN_NAME;
        int    topK       = DEFAULT_TOP_K;

        // Parse command-line arguments — manual switch, no external library needed.
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--index-dir"   -> indexDir   = args[++i];
                case "--topics-file" -> topicsFile = args[++i];
                case "--output-run"  -> outputFile = args[++i];
                case "--run-name"    -> runName    = args[++i];
                case "--top-k"       -> topK       = Integer.parseInt(args[++i]);
                default -> System.err.println("[WARN] Unknown argument: " + args[i]);
            }
        }

        Path indexPath  = Indexer.resolveRelativePath(indexDir);
        Path topicsPath = Indexer.resolveRelativePath(topicsFile);
        Path outputPath = Indexer.resolveRelativePath(outputFile);

        // Sanity checks — fail fast with a useful message rather than a cryptic NPE.
        if (!Files.exists(indexPath)) {
            System.err.println("[ERROR] Index directory not found: " + indexPath);
            System.err.println("        Please run Indexer first:");
            System.err.println("        java -cp target/*.jar cs4201.Indexer");
            System.exit(1);
        }
        if (!Files.exists(topicsPath)) {
            System.err.println("[ERROR] Topics file not found: " + topicsPath);
            System.exit(1);
        }

        System.out.println("[CS4201-Java-Retriever] BM25 k1=" + BM25_K1 + "  b=" + BM25_B);
        System.out.println("[CS4201-Java-Retriever] Index:   " + indexPath);
        System.out.println("[CS4201-Java-Retriever] Topics:  " + topicsPath);
        System.out.println("[CS4201-Java-Retriever] Output:  " + outputPath);
        System.out.println("[CS4201-Java-Retriever] Run name: " + runName);

        // Parse FIRE 2012 topics from XML.
        List<Topic> topics = parseTopics(topicsPath);
        System.out.println("[CS4201-Java-Retriever] Loaded " + topics.size() + " topics");
        if (topics.size() != 50) {
            System.err.println("[WARN] Expected 50 topics, got " + topics.size());
        }

        // Open the Lucene index (read-only).
        Directory directory = MMapDirectory.open(indexPath);
        DirectoryReader reader = DirectoryReader.open(directory);

        System.out.println("[CS4201-Java-Retriever] Index has " + reader.numDocs() + " documents");

        try {
            IndexSearcher searcher = new IndexSearcher(reader);
            // Similarity must match what was used at index time.
            searcher.setSimilarity(new BM25Similarity(BM25_K1, BM25_B));

            // EnglishAnalyzer — same stemmer and stopwords used at index time.
            Analyzer analyzer = new EnglishAnalyzer();

            // Query targets the "content" field (title + body concatenated at index time).
            QueryParser parser = new QueryParser("content", analyzer);

            // OR operator maximises recall; empirically best for FIRE 2012 short titles.
            parser.setDefaultOperator(QueryParser.Operator.OR);

            // Lucene 9.5+ stored-fields API.
            StoredFields storedFields = searcher.storedFields();

            // Ensure output directory exists before trying to write there.
            Files.createDirectories(outputPath.getParent());

            int totalWritten = 0;

            try (PrintWriter out = new PrintWriter(new BufferedWriter(
                    new OutputStreamWriter(
                            new FileOutputStream(outputPath.toFile()),
                            StandardCharsets.UTF_8)))) {

                for (Topic topic : topics) {
                    // Title-only queries; description+narrative hurt MAP on these topics.
                    String queryText = Indexer.normalizeText(topic.title());
                    if (queryText.isEmpty()) {
                        System.err.println("[WARN] Empty title for topic " + topic.qid() + ", skipping");
                        continue;
                    }

                    // Escape special Lucene syntax chars (e.g. +, :, ~) to prevent parse errors.
                    String escapedQuery = QueryParser.escape(queryText);
                    if (escapedQuery.trim().isEmpty()) continue;

                    // Parse the escaped query string into a Lucene Query object.
                    Query query;
                    try {
                        query = parser.parse(escapedQuery);
                    } catch (Exception e) {
                        System.err.println("[WARN] Query parse failed for topic " + topic.qid()
                                + " (\"" + queryText + "\"): " + e.getMessage());
                        continue;
                    }

                    TopDocs topDocs = searcher.search(query, topK);
                    ScoreDoc[] hits  = topDocs.scoreDocs;

                    // Write one TSV row per hit in TREC run format.
                    for (int rank = 1; rank <= hits.length; rank++) {
                        ScoreDoc hit = hits[rank - 1];

                        Document doc = storedFields.document(hit.doc);
                        String docId = doc.get("docno");

                        if (docId == null || docId.isEmpty()) {
                            docId = "LUCENE_DOC_" + hit.doc;
                        }

                        out.print(topic.qid() + "\tQ0\t" + docId + "\t" + rank
                                + "\t" + String.format("%.6f", hit.score)
                                + "\t" + runName + "\n");
                        totalWritten++;
                    }
                }

            }

            System.out.println("\n=== RETRIEVAL COMPLETE ===");
            System.out.println("topics_processed: " + topics.size());
            System.out.println("rows_written:     " + totalWritten);
            System.out.println("run_file:         " + outputPath);
            System.out.printf( "model:            BM25(k1=%.1f, b=%.1f)%n", BM25_K1, BM25_B);
            System.out.println("run_name:         " + runName);

        } finally {
            reader.close();
            directory.close();
        }
    }

    /**
     * Parses the FIRE 2012 topics XML file and returns a list of Topic records.
     * Uses the JDK DOM parser with XXE protections enabled.
     */
    static List<Topic> parseTopics(Path topicsFile) throws Exception {
        // Disable external entity resolution to prevent XXE injection.
        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", false);
        dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
        dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        dbf.setExpandEntityReferences(false);

        var db  = dbf.newDocumentBuilder();
        var doc = db.parse(topicsFile.toFile());

        List<Topic> topics = new ArrayList<>();
        NodeList topNodes = doc.getElementsByTagName("top");

        for (int i = 0; i < topNodes.getLength(); i++) {
            Element top = (Element) topNodes.item(i);

            String qid   = Indexer.normalizeText(tagText(top, "num"));
            String title = Indexer.normalizeText(tagText(top, "title"));
            String desc  = Indexer.normalizeText(tagText(top, "desc"));
            String narr  = Indexer.normalizeText(tagText(top, "narr"));

            if (qid.isEmpty()) {
                System.err.println("[WARN] Topic at index " + i + " has no <num> element, skipping");
                continue;
            }

            topics.add(new Topic(qid, title, desc, narr));
        }

        return topics;
    }

    /**
     * Return the text content of the first child element with the given tag name,
     * or "" if not found.  Equivalent to Python's {@code top.findtext(tagName) or ""}.
     */
    private static String tagText(Element parent, String tagName) {
        NodeList nodes = parent.getElementsByTagName(tagName);
        if (nodes.getLength() == 0) return "";
        return nodes.item(0).getTextContent();
    }
}
