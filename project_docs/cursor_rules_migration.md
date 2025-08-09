# Cursor Rules Migration Guide

## Current State

### ✅ Completed Cursor Rules
1. **`general-rules.mdc`** - Project overview and core principles (alwaysApply: true)
2. **`code-standards.mdc`** - Code quality standards (alwaysApply: true)
3. **`api-patterns.mdc`** - FastAPI development patterns (alwaysApply: false)
4. **`database-patterns.mdc`** - Database patterns and SQLAlchemy (alwaysApply: false)
5. **`testing-patterns.mdc`** - Testing patterns and best practices (alwaysApply: false)
6. **`computer-vision.mdc`** - Computer vision patterns (alwaysApply: false)
7. **`git-workflow.mdc`** - Git workflow and version control (alwaysApply: false)
8. **`project-structure.mdc`** - Project structure documentation (alwaysApply: false)
9. **`react-frontend.mdc`** ✅ **NEW** - React development patterns, testing, and best practices (alwaysApply: false)

### 📋 Project Docs Status

#### Keep for Now:
- `project_plan.md` - Development roadmap and phases
- `deployment_guide.md` - Deployment-specific details
- `react_frontend_guide.md` - Frontend patterns (not yet converted)

#### Consider Deprecating:
- `api_documentation.md` - Now covered in `api-patterns.mdc`
- `database_schema.md` - Now covered in `database-patterns.mdc`
- `testing_guide.md` - Now covered in `testing-patterns.mdc`

## Recommendations

### 1. Cursor Rules Configuration

**Always Apply (alwaysApply: true):**
- `general-rules.mdc` - Core project context
- `code-standards.mdc` - Essential coding standards

**Context-Specific (alwaysApply: false):**
- All other rule files - Apply only when working in specific areas

### 2. Project Docs Migration

#### Phase 1: Add Deprecation Notices
Add to the top of each markdown file that's been converted:

```markdown
> **Note**: This documentation has been migrated to cursor rules. 
> For the most up-to-date patterns, see `.cursor/rules/[rule-name].mdc`
```

#### Phase 2: Update README.md
Update the README to reference cursor rules instead of project docs for development patterns.

#### Phase 3: Gradual Removal
After cursor rules are proven comprehensive, remove the deprecated markdown files.

### 3. Future Cursor Rules

Consider creating these additional rule files:
- `deployment-patterns.mdc` - Deployment and infrastructure patterns
- `frontend-patterns.mdc` - React development patterns
- `security-patterns.mdc` - Security best practices

## Benefits of This Organization

1. **Focused Learning**: Developers can learn specific areas without being overwhelmed
2. **Better Performance**: Context-specific rules only apply when needed
3. **Easier Maintenance**: Each rule file can be updated independently
4. **Actionable Content**: Specific, implementable patterns
5. **Scalable Structure**: Easy to add new rule files for new areas

## Usage Guidelines

### For New Developers:
1. Start with `general-rules.mdc` for project overview
2. Use `code-standards.mdc` for all Python development
3. Reference specific rule files when working in those areas

### For Specific Tasks:
- **API Development**: Use `api-patterns.mdc`
- **Database Work**: Use `database-patterns.mdc`
- **Testing**: Use `testing-patterns.mdc`
- **Computer Vision**: Use `computer-vision.mdc`
- **Git Operations**: Use `git-workflow.mdc`

### For Project Management:
- **Project Structure**: Use `project-structure.mdc`
- **Overall Context**: Use `general-rules.mdc`
