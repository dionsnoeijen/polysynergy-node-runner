def find_groups_with_output(conns_data):
    groups_with_output = set()

    for conn in conns_data:
        source_group = conn.get("sourceGroupId")
        source_node = conn.get("sourceNodeId")
        target_group = conn.get("targetGroupId")
        target_node = conn.get("targetNodeId")

        # deze groep stuurt iets naar buiten als:
        # - de sourceGroupId bestaat
        # - én de targetGroupId is leeg of anders (dus niet binnen dezelfde group)
        # - én de sourceNodeId is NIET gelijk aan de sourceGroupId (dus niet een dummy buitenste verbinding)

        if (
            source_group
            and source_group != target_group
            and source_node != source_group
        ):
            groups_with_output.add(source_group)

    return groups_with_output