import pretext.resources
from scripts import fetch_core, utils


# Restore the original core directory and reinstall core resources into home/.ptx appropriately
def main() -> None:
    link_path = pretext.resources.resource_base_path() / "core"
    utils.remove_path(link_path)

    # fetch core resources to replace the symlinked core pretext script
    fetch_core.main()
    print("Restored original core directory and reinstalled core resources.")
    pretext.resources.install(reinstall=True)
    print("Finished unlinking core resources.")


if __name__ == "__main__":
    main()
