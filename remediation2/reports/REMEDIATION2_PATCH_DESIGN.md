# Remediation 2 patch design

## Scope

The new prompt patch is a new implementation, not a repaired copy of the malformed historical patch. It is stored at `patches/prompt_zeroization_new.patch` and has SHA-256 `720ee178f3a5d8218987cbc8cbeaff98e003624dc8a4cd119be6d0edc93008d9`.

## Ownership and ordering

In the pinned source, `server_queue` owns mutable `server_task` values until a task is launched. A slot previously stored the active task as `std::unique_ptr<const server_task>`, which made the historical cleanup lambda ill-formed. The new design changes only the slot's exclusive active owner to `std::unique_ptr<server_task>`. `task_prev` remains `std::unique_ptr<const server_task>` for the existing debug snapshot path. The status serializer reads through `const server_task *`, so it does not need to mutate the task.

The cleanup order is: complete the final legitimate task read and response construction; clear slot-owned generated strings and task-owned sensitive strings in `server_slot::reset`; move the cleaned task to `task_prev`; and clear final-result strings in `server_task_result_cmpl_final` after the HTTP serialization path has consumed the result object. The response is therefore not blanked before it is delivered.

## Buffers covered

`task_params::zeroize_sensitive_buffers` clears chat-parser and sampling generation prompts, reasoning-budget text, stop strings, response-field strings, and compatibility/control strings. `server_task::zeroize_sensitive_buffers` additionally clears CLI prompt and slot-action path strings. The final result destructor clears prompt, content, stopping text, response identifiers, and copied generation parameters.

## Secure erasure primitive

`server-secure-zero.cpp` calls `explicit_bzero` on supported Unix targets and uses a volatile-byte fallback on other targets. `zero_string` expands to the current capacity, explicitly clears the bytes, then clears the logical length. The compiled object has an unresolved `explicit_bzero` relocation, confirming that the glibc path was emitted for this build.

This design clears identified C++ buffers. It does not claim to clear every historical copy in HTTP JSON objects, allocator arenas, token-derived state, GPU memory, or process memory.
