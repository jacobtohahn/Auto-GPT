from promptgenerator import PromptGenerator


def get_prompt():
    """
    This function generates a prompt string that includes various constraints, commands, resources, and performance evaluations.

    Returns:
        str: The generated prompt string.
    """

    # Initialize the PromptGenerator object
    prompt_generator = PromptGenerator()

    # Add constraints to the PromptGenerator object
    prompt_generator.add_constraint("~4000 word limit for short term memory. Your short term memory is short, so immediately save important information to files.")
    prompt_generator.add_constraint("If you are unsure how you previously did something or want to recall past events, thinking about similar events will help you remember.")
    prompt_generator.add_constraint("No user assistance")
    prompt_generator.add_constraint('Exclusively use the commands listed in double quotes e.g. "command name"')
    prompt_generator.add_constraint("All content should be written in .md files using Markdown formatting unless a .csv file is warranted.")

    # Define the command list
    commands = [
        ("Google Search", "google", {"input": "<search>"}),
        ("Browse Website", "browse_website", {"url": "<url>", "question": "<what_you_want_to_find_on_website>"}),

        # Agents
        ("Start GPT Agent", "start_agent", {"name": "<name>", "task": "<short_task_desc>", "prompt": "<prompt>"}),
        ("Message GPT Agent", "message_agent", {"key": "<key>", "message": "<message>"}),
        ("List GPT Agents", "list_agents", {}),
        ("Delete GPT Agent", "delete_agent", {"key": "<key>"}),
        
        # File Stuff
        ("Read file", "read_file", {"file": "<file>"}),
        ("Write to file", "write_to_file", {"file": "<file>", "text": "<text>"}),
        ("Append to file", "append_to_file", {"file": "<file>", "text": "<text>"}),
        ("Delete file", "delete_file", {"file": "<file>"}),
        ("Copy File", "copy_file", {"source": "<source>", "destination": "<destination>"}),
        ("Move File", "move_file", {"source": "<source>", "destination": "<destination>"}),
        ("Rename File", "rename_file", {"source": "<source>", "destination": "<destination>"}),
        ("Search Files", "search_files", {"directory": "<directory>"}),
        
        # ("Create Directory", "create_directory", {"directory": "<directory>"}),
        ("Evaluate Directory", "evaluate_directory", {}),
        ("List Directories", "list_directories", {"directory": "<directory>"}),
        
        ("Task Complete (Shutdown)", "task_complete", {"reason": "<reason>"}),
        # ("Generate Image", "generate_image", {"prompt": "<prompt>"}),
        ("Do Nothing", "do_nothing", {}),
    ]

    # Add commands to the PromptGenerator object
    for command_label, command_name, args in commands:
        prompt_generator.add_command(command_label, command_name, args)

    # Add resources to the PromptGenerator object
    prompt_generator.add_resource("Internet access for searches and information gathering.")
    prompt_generator.add_resource("Long Term memory management.")
    prompt_generator.add_resource("GPT-3.5 powered Agents for delegation of simple tasks.")
    prompt_generator.add_resource("File management & directory evaluation.")

    # Add performance evaluations to the PromptGenerator object
    prompt_generator.add_performance_evaluation("Continuously review and analyze your actions to ensure you are performing to the best of your abilities and producing quality research output.")
    prompt_generator.add_performance_evaluation("Constructively evaluate the file system and implement strategies that allow information to coalesce into folders.")
    prompt_generator.add_performance_evaluation("Constructively self-criticize your big-picture behavior from time to time.")
    prompt_generator.add_performance_evaluation("Reflect on past decisions, strategies, and output to refine your approach.")
    prompt_generator.add_performance_evaluation("Every command has a cost, so be smart and efficient. Aim to complete tasks in the least number of steps.")

    # Generate the prompt string
    prompt_string = prompt_generator.generate_prompt_string()

    return prompt_string
