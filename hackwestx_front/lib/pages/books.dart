import 'package:flutter/material.dart';

class Books extends StatelessWidget {
  const Books({super.key});

  @override
  Widget build(BuildContext context) {
    final books = _books;

    return Container(
      width: double.infinity,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF0B1220), Color(0xFF0B1220)],
        ),
      ),
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(24, 32, 24, 40),
        itemCount: books.length + 1,
        separatorBuilder: (_, __) => const SizedBox(height: 12),
        itemBuilder: (context, i) {
          if (i == 0) {
            return Center(
              child: Text(
                'Books Used for Referencing',
                style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
              ),
            );
          }
          final book = books[i - 1];
          return Align(
            alignment: Alignment.topCenter,
            child: _BookCard(book: book),
          );
        },
      ),
    );
  }
}

class BookRef {
  const BookRef({
    required this.title,
    required this.author,
    required this.investorTag,
    required this.coverAsset,
  });

  final String title;
  final String author;
  final String investorTag;
  final String coverAsset;
}

final _books = <BookRef>[
  const BookRef(
    title: 'The Snowball and Financial Analysis',
    author: 'Warren Buffett',
    investorTag: 'Buffett',
    coverAsset: 'assets/books/buffett.jpg',
  ),
  const BookRef(
    title: 'One Up On Wall Street',
    author: 'Peter Lynch',
    investorTag: 'Lynch',
    coverAsset: 'assets/books/lynch.jpg',
  ),
  const BookRef(
    title: 'The Intelligent Investor',
    author: 'Benjamin Graham',
    investorTag: 'Graham',
    coverAsset: 'assets/books/graham.jpg',
  ),
  const BookRef(
    title: 'The Alchemy of Finance',
    author: 'George Soros',
    investorTag: 'Soros',
    coverAsset: 'assets/books/soros.jpg',
  ),
  const BookRef(
    title: 'Investing the Templeton Way',
    author: 'John Templeton',
    investorTag: 'Templeton',
    coverAsset: 'assets/books/templeton.jpg',
  ),
  const BookRef(
    title: 'Margin of Safety',
    author: 'Seth Klarman',
    investorTag: 'Klarman',
    coverAsset: 'assets/books/klarman.jpg',
  ),
];

class _BookCard extends StatelessWidget {
  const _BookCard({required this.book});

  final BookRef book;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;

    return ConstrainedBox(
      constraints: const BoxConstraints(maxHeight: 400, maxWidth: 500),
      child: Row(
        children: [
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 300, maxWidth: 200),
            child: AspectRatio(
              aspectRatio: 3 / 4,
              child: Image.asset(book.coverAsset),
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Text(
                book.title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: t.titleMedium?.copyWith(fontWeight: FontWeight.w800),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
