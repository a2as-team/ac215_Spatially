from utils.smart_arg_parser import SmartArgItem, SmartArgParser

if __name__ == "__main__":
    schema = {
        "job_type": SmartArgItem(
            flags=["--job-type"],
            prompt="Type of job to run",
            arg_type=str,
            required=True,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()
    job_type = args["job_type"]