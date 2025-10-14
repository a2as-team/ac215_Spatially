# Development Plans Parser

If you want to run the parser locally, you need to have Ollama running.

First install Ollama: https://ollama.com/

After downloading, you can have ollama runnable with your cli.

For now we will default to using llama3.2 because it is the smallest model that is still capable of parsing the development plans.

```bash
ollama run llama3.2
```

The above command will automatically download the model if the model is not already downloaded.