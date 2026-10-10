using System;
using System.Diagnostics;
using System.IO;
using System.Text;

// OWLViz 5.0.3 invokes: dot <scratch-file> -q -o <same-scratch-file>.
// Graphviz on Windows cannot open its input for output while reading it.
// Place this launcher beside dot.exe and select it in OWLViz preferences.
internal static class OwlVizDot
{
    private static string QuoteArgument(string argument)
    {
        var quoted = new StringBuilder("\"");
        int slashes = 0;
        foreach (char character in argument)
        {
            if (character == '\\')
            {
                slashes++;
                continue;
            }
            quoted.Append('\\', character == '"' ? slashes * 2 + 1 : slashes);
            quoted.Append(character);
            slashes = 0;
        }
        quoted.Append('\\', slashes * 2);
        quoted.Append('"');
        return quoted.ToString();
    }

    private static int Main(string[] args)
    {
        string temporaryOutput = null;
        try
        {
            string realDot = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "dot.exe");
            string[] forwarded = (string[])args.Clone();
            bool inPlace = args.Length == 4 && args[1] == "-q" && args[2] == "-o"
                && String.Equals(Path.GetFullPath(args[0]), Path.GetFullPath(args[3]),
                    StringComparison.OrdinalIgnoreCase);

            if (inPlace)
            {
                temporaryOutput = Path.Combine(Path.GetDirectoryName(Path.GetFullPath(args[3])),
                    "owlviz-layout-" + Guid.NewGuid().ToString("N") + ".tmp");
                forwarded[3] = temporaryOutput;
            }

            var start = new ProcessStartInfo(realDot,
                String.Join(" ", Array.ConvertAll(forwarded, QuoteArgument)));
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            using (Process process = Process.Start(start))
            {
                process.WaitForExit();
                if (process.ExitCode != 0)
                    return process.ExitCode;
            }

            // Graphviz has now closed the input. Only replace it after success.
            if (inPlace)
                File.Copy(temporaryOutput, args[3], true);
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine("OWLViz Graphviz launcher: " + error.Message);
            return 1;
        }
        finally
        {
            if (temporaryOutput != null)
            {
                try { File.Delete(temporaryOutput); }
                catch (IOException) { }
                catch (UnauthorizedAccessException) { }
            }
        }
    }
}
