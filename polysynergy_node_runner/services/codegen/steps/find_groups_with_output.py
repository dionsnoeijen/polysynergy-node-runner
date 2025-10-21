def find_groups_with_output(conns_data):
    groups_with_output = set()

    for conn in conns_data:
        source_group = conn.get("sourceGroupId")
        source_node = conn.get("sourceNodeId")
        target_group = conn.get("targetGroupId")
        target_node = conn.get("targetNodeId")
        is_in_group = conn.get("isInGroup")

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
            print(f"[GROUPS_WITH_OUTPUT] Scenario 1 matched - added {source_group}")

        # een parent group heeft ook output als een nested group naar de boundary stuurt:
        # Scenario 1: targetGroupId is expliciet gezet
        if (
            target_group
            and source_group != target_group
            and target_node == target_group
        ):
            groups_with_output.add(target_group)
            print(f"[GROUPS_WITH_OUTPUT] Scenario 2 matched - added {target_group}")

        # Scenario 2: connection naar group boundary (targetNodeId == isInGroup)
        # Dit gebeurt als een nested group connect naar zijn parent group boundary
        if (
            is_in_group
            and target_node == is_in_group
            and source_group
            and source_group != is_in_group
        ):
            groups_with_output.add(is_in_group)
            print(f"[GROUPS_WITH_OUTPUT] Scenario 3 matched - added {is_in_group}")
            print(f"  Connection details: isInGroup={is_in_group}, targetNode={target_node}, sourceGroup={source_group}")

    print(f"[GROUPS_WITH_OUTPUT] Final result: {groups_with_output}")
    return groups_with_output