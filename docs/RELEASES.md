# Named releases

Most version bumps are just tags. Every so often, a **named release** gathers
the bumps since the last one under a codename, with a short note and a
release-notes video of about a minute. Every videobuilder instance shows it
on its What's new page, so a fresh self-hosted install sees it too.

## Codenames

Codenames are film-craft words, one per letter, in alphabetical order. The
next release takes the next letter. Each also gets a headline: one line on
what the release is about.

| Letter | Codename | Headline |
|---|---|---|
| A | Aperture | Films made of clips (v0.1.87) |
| B | Bokeh | Sound effects, type and a stick figure (v0.1.99) |

Some words for the next few letters (pick any word that fits the letter):

- C: Cutaway, Crane
- D: Dolly, Dissolve
- E: Establishing, Edit
- F: Fade, Focus pull
- G: Grip, Gaffer
- H: Handheld, Headroom
- I: Iris, Insert
- J: Jib, Jump cut
- K: Key light, Keyframe

## The entry file

Each named release is a text file, `videobuilder/release_notes/<id>.md`,
where `<id>` is the codename in lower case (`aperture.md`):

    ---
    codename: Aperture
    headline: Films made of clips
    date: 2026-10-17
    tag: v0.1.87
    to: 0.1.87
    video-9x16: release-notes-9x16.mp4
    video-16x9: release-notes-16x9.mp4
    ---
    A video can now be a film made of clips: ...

    - A note can target one clip. ...

- `to` is the last version the release covers. There is no `from`: a
  release covers everything since the previous one, so the page shows
  "0.1.88–0.1.95" for a release after one that ended at 0.1.87, and "up to
  0.1.87" for the first one.
- `tag` is the GitHub release the videos are attached to.
- `video-9x16`, `video-16x9` and `video-1x1` are optional: the file names of
  the release's MP4 assets. Phones get the 9:16 one, wide screens the 16:9 one.
- The notes are plain paragraphs and lines starting `- ` as a list. Nothing
  else is markup: it's all shown as text.

An instance shows a release once it runs version `to` or later. The file is
committed text; the videos never go in git.

## Publishing one

1. Bump the version and tag it as usual (`v0.1.87`).
2. Make the release-notes video with videobuilder in 9:16 and 16:9.
3. Write `videobuilder/release_notes/<codename>.md` as above, add its row to
   the table here, and commit both.
4. Create the GitHub release on the tag, with the videos as assets. Their
   names must match the entry file:

       gh release create v0.1.87 release-notes-9x16.mp4 release-notes-16x9.mp4 \
           --title "Aperture: Films made of clips" \
           --notes-file videobuilder/release_notes/aperture.md

Each instance's server downloads the videos from
`https://github.com/<repo>/releases/download/<tag>/<file>` the first time
someone opens What's new, saves them in its state directory and serves them
itself. Until then, and on instances that turn remote videos off, the entry
shows its text only.
