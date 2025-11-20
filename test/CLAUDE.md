### Writing Effective Tests

**ARCHITECT writes architectural tests that**:

- Define system boundaries and contracts
- Validate pattern compliance
- Ensure state immutability
- Test critical game mechanics

**Good test characteristics**:

1. **Readable as documentation**

   ```gdscript
   func test_player_cannot_choose_diplomatic_when_too_violent():
       # Story: A violent player loses access to peaceful solutions
       var state = GameState.create_test_state()
       state = PlayerSystem.modify_conviction(state, "violence_thoughts", 8)

       # When checking quest approach availability
       var can_use = QuestSystem.can_use_approach(state, "prisoner_rescue", "diplomatic")

       # Then diplomatic approach is locked
       assert_false(can_use, "High violence should lock diplomatic options")
   ```

1. **Test behavior, not implementation**

   ```gdscript
   # BAD - Tests internal details
   func test_quest_internal_state():
       assert(quest._internal_counter == 5)  # Brittle!

   # GOOD - Tests observable behavior
   func test_quest_completion_unlocks_next_area():
       var result = complete_quest(state, "escape_prison")
       assert(result.world.unlocked_areas.has("rebel_camp"))
   ```

1. **One concept per test**

   ```gdscript
   # BAD - Kitchen sink test
   func test_entire_quest_flow_and_rewards_and_prerequisites():
       # 200 lines of mixed concerns...

   # GOOD - Focused tests
   func test_quest_requires_prerequisite()
   func test_quest_grants_rewards()
   func test_quest_approach_degrades_stats()
   ```

### Test Anti-Patterns to Avoid

**1. "Fake Pass" Tests**

```gdscript
# BAD - Test that always passes
func test_something():
    var result = broken_function()
    assert(true)  # Useless!
```

**2. "Change Detector" Tests**

```gdscript
# BAD - Breaks with any refactor
func test_exact_string_output():
    assert(message == "Welcome, brave warrior, to the land of...")
    # Any text tweak breaks this
```

**3. "God Object" Tests**

```gdscript
# BAD - Tests everything at once
func test_entire_game():
    # 500 lines testing unrelated systems
```

### CODER's Test Responsibilities

While ARCHITECT writes architectural tests, CODER must:

1. **Run all tests before marking work complete**
2. **Add edge case tests discovered during implementation**
3. **Update tests when requirements change**
4. **Never disable failing tests—fix the cause**
5. **Write integration tests for complex workflows**

### Test Coverage Philosophy

**Focus areas (high coverage needed)**:

- State mutations (every reducer path)
- Save/load integrity
- Quest prerequisites and outcomes
- Degradation calculations
- Dialogue→State bridges

**Lower priority (basic coverage OK)**:

- UI layout
- Visual effects
- Debug commands
- Placeholder assets

### When Tests Seem Wrong

If CODER finds a test that seems incorrect:

1. **First assume the test is right** - It may reveal misunderstood requirements
2. **Trace test intent** - What behavior is it protecting?
3. **Consult ARCHITECT** - Before changing any architectural test
4. **Document changes** - If test needs updating, explain why

### Integration Test Guidelines

Integration tests verify the full pipeline works:

```gdscript
func test_quest_dialogue_to_state_integration():
    # Setup: Player with specific stats
    var state = create_test_state_with_convictions({"empathy_thoughts": 5})

    # Action: Complete quest via diplomatic approach
    state = GameStateActions.complete_quest(state, "rescue_prisoner", "diplomatic")

    # Verify: Multiple systems updated correctly
    assert(state.quests.completed.has("rescue_prisoner"))
    assert(state.player.flexibility_charisma > 0)
    assert(state.world.flags.has("prisoner_freed_peacefully"))

    # Verify: Next quest is available
    assert(QuestSystem.can_start_quest(state, "report_to_leader"))
```

**Key principle**: Integration tests catch issues unit tests miss, especially in the Dialogic→GameState pipeline.
